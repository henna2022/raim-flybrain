"""라이체스 평가 DB를 체스 신경망 학습용 780비트 + 둘 차례 쪽 승률로 바꾼다.
원본 jsonl.zst 22 GB는 단일 zstd 프레임이라 가운데를 못 읽는다. 대신 라이체스 공식 허깅페이스 미러의
파케이 샤드에서 필요한 행그룹의 필요한 열만 구간 요청으로 받는다 (행그룹 하나에 약 17 MB, 국면 약 47만).
검증은 학습에 안 쓴 행그룹에서 통째로 뽑는다. 한 대국의 이웃 국면은 같은 행그룹에 뭉쳐 있어서다.
산출: dl/chess/train.npz, val.npz, meta.json
사용: python dl/chess_data.py              (자체 검사, 망 없이 돈다)
      python dl/chess_data.py 500000       (파일럿 국면)
      python dl/chess_data.py 2000000      (본학습)
      python dl/chess_data.py check        (허깅페이스에 닿는지만 확인, 받지 않음)"""
import json, math, os, subprocess, sys
from array import array
try:                       # check 는 가상환경을 만들기 전에 도는 명령이라 넘파이 없이도 돌아야 한다
    import numpy as np
except ImportError:
    np = None

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, 'chess')
URL = 'https://huggingface.co/datasets/Lichess/chess-position-evaluations/resolve/main/data/data_%04d.parquet'
SHARD = 10                               # 샤드 가운데 하나
TRAIN_GROUPS, VAL_GROUP = (0, 9, 18, 27), 36   # 행그룹은 샤드 안에 퍼뜨려 뽑고, 검증은 학습에 안 쓴 행그룹 하나에서만
COLS = ('fen', 'depth', 'cp', 'mate')    # line 열(행그룹의 59%)은 안 받는다
TAIL = 400 * 1024                        # 파케이 꼬리표(스키마·행그룹 오프셋)가 들어갈 만큼
MIN_DEPTH = 20                           # 이 미러는 이미 depth>=20으로 걸러져 있다(행그룹 45개 전부 최소 20). 방어용으로 남긴다
PIECES = 'PNBRQKpnbrqk'


def win_white(cp, mate):
    """라이체스 winningChances.ts와 같은 값(상수 -0.00368208). 결과는 백이 이길 가능성 0~1"""
    assert mate != 0, 'mate 0은 있을 수 없어요 (부호가 없어서 라벨이 정반대로 붙는다)'
    x = (21 - min(10, abs(mate))) * 100 * (1 if mate > 0 else -1) if mate is not None else max(-1000, min(1000, cp))
    return 1.0 / (1.0 + math.exp(-0.00368208 * x))


def label(stm, cp, mate):
    """둘 차례 쪽이 이길 가능성. 백 기준 값을 여기 한 곳에서만 뒤집는다"""
    p = win_white(cp, mate)
    return 1 - p if stm == 'b' else p


def encode(fen):
    """FEN을 780비트 인덱스 목록으로. 불법 국면이면 None. 흑 차례면 정규화해서 대문자가 항상 둘 차례 쪽이 되게 한다"""
    part = fen.split()
    if len(part) < 4: return None
    board, stm, cast, ep = part[:4]
    rows = board.split('/')
    if len(rows) != 8 or stm not in ('w', 'b'): return None
    n = 0
    for row in rows:
        wide = 0
        for c in row:
            if c in PIECES: wide += 1; n += 1
            elif '1' <= c <= '8': wide += int(c)
            else: return None
        if wide != 8: return None
    if not 2 <= n <= 32 or board.count('K') != 1 or board.count('k') != 1: return None
    if board.count('P') > 8 or board.count('p') > 8: return None   # 폰 51개짜리 같은 더러운 줄을 여기서 거른다
    if stm == 'b':                                                 # 위아래를 뒤집고 대소문자를 바꾸면 둘 차례 쪽이 대문자가 된다
        rows = [r.swapcase() for r in reversed(rows)]
        cast = cast.swapcase()                                     # 앙파상은 열만 쓰므로 그대로 둔다
    bits = []
    for r, row in enumerate(rows):
        f = 0
        for c in row:
            if c in PIECES: bits.append(PIECES.index(c) * 64 + r * 8 + f); f += 1
            else: f += int(c)
    bits += [768 + 'KQkq'.index(c) for c in cast if c in 'KQkq']
    if 'a' <= ep[0] <= 'h': bits.append(772 + ord(ep[0]) - 97)
    return sorted(bits)


def pack(idx):
    """비트 인덱스 목록 → uint8[98] (780비트를 784로 패딩, 뒤 4비트는 항상 0)"""
    b = np.zeros(784, np.uint8); b[idx] = 1
    return np.packbits(b)


def grab(f, url, start, n):
    """구간 요청 한 번. 받은 바이트 수가 다르면 그 자리에서 멈춘다(다시 실행하면 이어서 받는다)"""
    out = subprocess.run(['curl', '-sfL', '--http1.1', '--retry', '10', '--retry-all-errors', '--retry-delay', '3',
                          '--speed-limit', '1024', '--speed-time', '30',   # 소켓만 살아 있고 데이터가 안 오면 끊고 재시도 (회사망)
                          '-r', f'{start}-{start + n - 1}', url], capture_output=True).stdout
    if len(out) != n: sys.exit(f'  [실패] {n}바이트를 받으려 했는데 {len(out)}바이트 왔어요. 다시 실행하면 이어서 받아요.')
    f.seek(start); f.write(out)


def save_log(f, log, got):
    """이어받기 기록. 이게 깨지면 받아 둔 구간을 통째로 잃으니 바이트를 먼저 앉히고 tmp + os.replace로 쓴다"""
    f.flush(); os.fsync(f.fileno())
    json.dump(got, open(log + '.tmp', 'w'), ensure_ascii=False); os.replace(log + '.tmp', log)


def head(shard):
    """꼬리표 400 KB만 받아 희소 파일을 열어 둔다. 돌려주는 got에 이미 받은 구간 목록이 들어 있다"""
    import pyarrow.parquet as pq
    url, path = URL % shard, os.path.join(DIR, 'data_%04d.parquet' % shard)
    log = os.path.join(DIR, 'head_s%d.json' % shard)
    info = subprocess.run(['curl', '-sIL', '-m', '60', url], capture_output=True, text=True).stdout
    sizes = [int(l.split(':', 1)[1]) for l in info.splitlines() if l.lower().startswith('content-length')]
    if not sizes: sys.exit('  [실패] 허깅페이스 응답에 크기가 없어요. python dl/chess_data.py check 로 확인해 주세요.')
    size = max(sizes)                                  # -L이라 302 응답의 짧은 길이도 같이 온다
    try:
        got = json.load(open(log)) if os.path.exists(log) else {}
    except (ValueError, OSError):
        sys.exit(f'  [실패] 이어받기 기록이 깨졌어요. {log} 를 지우면 처음부터 다시 받아요.')
    if got.get('size') != size or not os.path.exists(path) or os.path.getsize(path) != size:
        with open(path, 'wb') as f: f.truncate(size)   # 희소 파일: ls -l은 2 GB로 보여도 du는 실제 받은 만큼만
        got = {'size': size, 'url': url, 'ranges': [], 'bytes': 0}
    with open(path, 'r+b') as f:
        if 'tail' not in got['ranges']:
            f.seek(0); f.write(b'PAR1')                # 앞 4바이트 매직이 있어야 파케이로 읽힌다
            grab(f, url, size - TAIL, TAIL)
            got['ranges'].append('tail'); got['bytes'] += TAIL
            save_log(f, log, got)
    return path, log, got, pq.ParquetFile(path).metadata


def fetch_groups(shard, groups):
    """행그룹마다 COLS 열의 구간만 받는다(행그룹당 약 17 MB, 국면 약 47만). 받은 목록은 남겨 두고 다음 실행 때 건너뛴다"""
    path, log, got, meta = head(shard)
    with open(path, 'r+b') as f:
        for g in groups:
            if g >= meta.num_row_groups: sys.exit(f'  [실패] 행그룹 {g}이 없어요 (이 샤드는 {meta.num_row_groups}개).')
            rg = meta.row_group(g)
            for i in range(rg.num_columns):
                c = rg.column(i)
                key = f'{g}:{c.path_in_schema}'
                if c.path_in_schema not in COLS or key in got['ranges']: continue
                grab(f, got['url'], c.dictionary_page_offset or c.data_page_offset, c.total_compressed_size)
                got['ranges'].append(key); got['bytes'] += c.total_compressed_size
                save_log(f, log, got)
            print(f'행그룹 {g} 준비됨 ({got["bytes"] / 2**20:.0f} MB 받음)', flush=True)
    return path, got['bytes']


def rows(path, groups):
    """같은 fen은 연속으로 붙어 있으므로 묶음마다 depth가 가장 깊은 행 하나만 내보낸다"""
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    for g in groups:
        t = pf.read_row_group(g, columns=list(COLS))
        fen, depth, cp, mate = (t.column(c).to_pylist() for c in COLS)
        i = 0
        while i < len(fen):
            j = i
            while j + 1 < len(fen) and fen[j + 1] == fen[i]: j += 1
            b = max(range(i, j + 1), key=lambda k: depth[k] or 0)   # 동점이면 첫 행 = 그 탐색의 pvs[0](최선수). 이 미러는 multi-PV를 행으로 펼쳐 두므로 순서를 바꾸면 안 된다
            yield fen[i], cp[b], mate[b], depth[b]
            i = j + 1


def build(target, shard=SHARD, groups=TRAIN_GROUPS, val_group=VAL_GROUP):
    """국면을 모아 train.npz / val.npz / meta.json으로 떨군다. 목표를 채우면 남은 행그룹은 받지도 않는다"""
    assert val_group not in groups, '검증 행그룹이 학습에 섞였다'
    os.makedirs(DIR, exist_ok=True)
    bits = {'train': bytearray(), 'val': bytearray()}
    ys = {'train': array('f'), 'val': array('f')}
    seen, stat = set(), dict(rows_read=0, dropped_illegal=0, dropped_no_eval=0, dropped_shallow=0, dropped_duplicate=0)
    downloaded, used = 0, {'train': [], 'val': []}
    for k, gs, want in [('train', groups, target), ('val', (val_group,), max(1, target // 20))]:
        for g in gs:
            path, downloaded = fetch_groups(shard, [g])
            used[k].append(g)
            for fen, cp, mate, depth in rows(path, [g]):
                stat['rows_read'] += 1
                if (depth or 0) < MIN_DEPTH: stat['dropped_shallow'] += 1; continue
                if cp is None and mate is None: stat['dropped_no_eval'] += 1; continue
                idx = encode(fen)
                if idx is None: stat['dropped_illegal'] += 1; continue
                b = pack(idx).tobytes()
                if b in seen: stat['dropped_duplicate'] += 1; continue   # 거울 관계인 두 국면도 여기서 하나로 합쳐진다
                seen.add(b)
                bits[k] += b; ys[k].append(label(fen.split()[1], cp, mate))
                if len(ys[k]) >= want: break
            if len(ys[k]) >= want: break
    for k in ('train', 'val'):
        tmp = os.path.join(DIR, k + '.tmp.npz')
        np.savez(tmp, bits=np.frombuffer(bytes(bits[k]), np.uint8).reshape(-1, 98), y=np.frombuffer(ys[k], np.float32))
        os.replace(tmp, os.path.join(DIR, k + '.npz'))
    meta = dict(n_train=len(ys['train']), n_val=len(ys['val']), target=target, shard=shard,
                train_groups=used['train'], val_groups=used['val'],
                min_depth=MIN_DEPTH, bytes_downloaded=downloaded, url=URL % shard,
                label_mean=round(float(np.mean(ys['train'])), 4) if ys['train'] else None, **stat)
    meta['_note'] = (f'표본은 샤드 {shard}의 행그룹 {used["train"]}(학습) · {used["val"]}(검증)에서만 뽑았다. '
                     '검증을 학습에 안 쓴 행그룹에서 통째로 뽑는 이유는 한 대국의 이웃 국면이 같은 행그룹에 뭉쳐 있어서다. '
                     f'이 미러는 depth>={MIN_DEPTH}로 이미 걸러져 있다. '
                     '갈래 사이 비교는 같은 데이터라 유효하지만, 절대 수치를 밖에 말할 때는 이 표본 조건을 같이 적어야 한다.')
    json.dump(meta, open(os.path.join(DIR, 'meta.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(meta, indent=1, ensure_ascii=False))
    for k, want in [('train', target), ('val', max(1, target // 20))]:
        if len(ys[k]) < want: print(f'[주의] {k} 목표 {want}개를 못 채웠어요. TRAIN_GROUPS·VAL_GROUP에 행그룹을 더 넣어 주세요.')


def need_numpy():
    if np is None: sys.exit('  [실패] 넘파이가 없어요. bash desktop/setup_dl.sh 를 먼저 돌리면 같이 깔려요')


def check():
    """허깅페이스와 라이체스 원본에 닿는지만 본다 (HEAD 두 개, 받지 않는다)"""
    for name, url in [('허깅페이스 파케이', URL % SHARD), ('라이체스 원본', 'https://database.lichess.org/lichess_db_eval.jsonl.zst')]:
        out = subprocess.run(['curl', '-sIL', '-m', '30', url], capture_output=True, text=True).stdout
        code = [l.split()[1] for l in out.splitlines() if l.startswith('HTTP/')]
        size = max([int(l.split(':', 1)[1]) for l in out.splitlines() if l.lower().startswith('content-length')], default=0)
        print(f'{name}: 상태 {code or "응답 없음"} · 크기 {size / 2**20:.0f} MB')


def mirror(fen):
    """검사용: 색을 통째로 뒤집은 국면 (위아래 뒤집기 + 대소문자 + 둘 차례 반전)"""
    board, stm, cast, ep = fen.split()[:4]
    return ' '.join(['/'.join(r.swapcase() for r in reversed(board.split('/'))), 'b' if stm == 'w' else 'w',
                     cast.swapcase(), ep if ep == '-' else ep[0] + {'3': '6', '6': '3'}.get(ep[1], ep[1])])


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    if arg == 'check': check(); sys.exit()
    if arg != 'selftest':
        if not arg.isdigit(): sys.exit('  [실패] 국면 수는 숫자로 적어 주세요. 예: python dl/chess_data.py 500000')
        need_numpy(); build(int(arg)); sys.exit()

    assert round(win_white(0, None), 4) == 0.5
    assert round(win_white(100, None), 5) == 0.59103
    assert round(win_white(1000, None), 5) == 0.97545
    assert round(win_white(None, 1), 5) == 0.99937
    assert win_white(50000, None) == win_white(1000, None)            # 메이트 누출값(±20000)이 잘리나
    assert abs(win_white(-300, None) + win_white(300, None) - 1) < 1e-12

    START = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -'
    BLACK = 'r5k1/R4pb1/4rnpp/1p2p3/4P1P1/3NBP2/1PP4P/4K2R b K -'     # 실제 데이터에 있던 줄
    EP = 'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6'
    for f, c in [(START, 25), (BLACK, -140), (EP, 60)]:
        m = mirror(f); a, b = f.split()[1], m.split()[1]
        assert encode(f) == encode(m), f                              # 정규화가 맞으면 두 비트집합이 같다
        assert abs(label(a, c, None) - label(b, -c, None)) < 1e-9, f   # 같은 국면이니 둘 차례 쪽 승률도 같다
        assert abs(label(a, c, None) + label(b, c, None) - 1) < 1e-9, f  # 둘 차례만 바뀌면 뒤집힌다

    assert len(encode(START)) == 36                                   # 기물 32 + 캐슬링 4, 앙파상 없음
    assert max(encode(EP)) == 774 and encode(EP).count(774) == 1      # 앙파상 c열 = 772 + 2
    assert encode('7K/PPPPPPPP/PPPPPPPP/8/8/8/8/q6k b - -') is None   # 폰이 8개를 넘는 불법 국면
    assert encode('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQ1BNR w KQkq -') is None   # 백 킹 없음
    assert encode('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNRX w KQkq -') is None  # 랭크 폭이 8이 아님
    assert label('w', 170, None) > 0.5 > label('b', 160, None)        # 실제 이웃 두 줄(백 cp170 → 흑 cp160)
    assert label('b', None, 3) < 0.01                                 # 흑 차례인데 백이 3수 만에 메이트
    assert max(range(3), key=lambda k: [30, 30, 25][k]) == 0           # 최고깊이 동점이면 첫 행(그 탐색의 pvs[0])을 골라야 한다
    try: win_white(None, 0); ok0 = False
    except AssertionError: ok0 = True
    assert ok0, 'mate 0을 그냥 라벨로 바꿨다'
    if np is not None:                                                # 넘파이가 없으면 비트 포장 검사만 건너뛴다
        assert np.packbits(np.zeros(784, np.uint8)).shape == (98,)
        assert np.unpackbits(pack(encode(START))).sum() == 36         # 팩했다 풀어도 켜진 비트 수가 같나
    print('selftest ok | 시작국면 비트', len(encode(START)), '| cp170 백차례', round(label('w', 170, None), 3))
