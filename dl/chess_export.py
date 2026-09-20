"""파일럿 검증 판에서 퍼즐 화면용 자료를 뽑는다. 태블릿은 모델을 돌리지 않고 이 답을 재생한다.
고르는 판은 유불리가 뚜렷한 판(|승률 - 0.5| >= 0.05)뿐이다. 우리가 성적을 잰 것도 그 판들이라
화면에서 쌓이는 점수가 report.json 의 숫자와 같은 뜻이 된다.
산출: viz/chess_puzzles.json
사용: python dl/chess_export.py            (자체 검사)
      python dl/chess_export.py 300        (퍼즐 300개 뽑기)
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'chess')
RUNS = os.path.join(OUT, 'runs')
VIZ = os.path.join(HERE, '..', 'viz')
PIECES = 'PNBRQKpnbrqk'
MARGIN = 0.05                 # chess_train.MARGIN 과 같아야 한다
FLY, NET = 'C0_s1', 'C3_s3'   # 초파리 뇌는 세 시드 중 중앙값 시드, 보통 신경망은 유일한 시드
SEED = 7                      # 어떤 판을 뽑을지 고정한다 (다시 돌려도 같은 퍼즐)


def board_of(row):
    """98바이트로 눌러 담은 780비트를 8x8 판 글자로 되돌린다. 맨 앞 8글자가 8번째 줄이다.
    거울 인코딩이라 대문자가 늘 둘 차례 쪽이어서, 화면에서 대문자를 흰 편으로 그리면 된다."""
    on = np.flatnonzero(np.unpackbits(row)[:768])
    sq = ['.'] * 64
    for i in on:
        sq[i % 64] = PIECES[i // 64]
    return ''.join(sq)


def load():
    z = np.load(os.path.join(OUT, 'val.npz'))
    preds = {k: np.load(os.path.join(RUNS, k + '_val.npy')) for k in (FLY, NET)}
    return z['bits'], z['y'], preds


def pick(n, bits, y, preds):
    """유불리가 뚜렷한 판에서 n개를 고른다. 초파리 뇌가 맞힌 판과 틀린 판이 실제 비율대로 섞인다"""
    idx = np.flatnonzero(np.abs(y - 0.5) >= MARGIN)
    take = np.random.default_rng(SEED).permutation(idx)[:n]
    take = take[np.argsort(-np.abs(y[take] - 0.5))]          # 쉬운 판부터 (유불리가 큰 순서)
    out = []
    for i in take:
        out.append({'b': board_of(bits[i]),
                    'y': round(float(y[i]), 4),
                    'f': round(float(preds[FLY][i]), 4),
                    'n': round(float(preds[NET][i]), 4)})
    return out


def grade(items):
    """뽑은 퍼즐에서 두 갈래가 몇 %를 맞히나. report.json 의 전체 성적과 비슷해야 한다"""
    hit = lambda k: round(float(np.mean([(it[k] > .5) == (it['y'] > .5) for it in items])), 4)
    return {'fly': hit('f'), 'net': hit('n')}


if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else 'selftest'
    bits, y, preds = load()

    if arg == 'selftest':
        b = board_of(bits[0])
        assert len(b) == 64 and b.count('K') == 1 and b.count('k') == 1, b
        items = pick(200, bits, y, preds)
        assert len(items) == 200 and all(abs(it['y'] - .5) >= MARGIN for it in items)
        assert all(it['b'].count('K') == 1 and it['b'].count('k') == 1 for it in items)
        assert len({it['b'] for it in items}) == 200, '같은 판이 두 번 나왔어요'
        full = {k: round(float(np.mean((preds[v] [np.abs(y - .5) >= MARGIN] > .5) ==
                                       (y[np.abs(y - .5) >= MARGIN] > .5))), 4)
                for k, v in (('fly', FLY), ('net', NET))}
        g = grade(items)
        assert g['net'] > g['fly'], (g, '보통 신경망이 더 잘해야 맞습니다')
        print(f"selftest ok | 뽑은 200판 초파리 {g['fly']} 보통망 {g['net']} | 전체 {full}")
        sys.exit()

    if not arg.isdigit():
        sys.exit('  [실패] 퍼즐 수는 숫자로 적어 주세요. 예: python dl/chess_export.py 300')
    items = pick(int(arg), bits, y, preds)
    rep = json.load(open(os.path.join(OUT, 'report.json'), encoding='utf-8'))
    data = {'_note': '파일럿 검증 판(학습에 안 쓴 판)에서 유불리가 뚜렷한 것만 골랐어요. '
                     'b는 8x8 판을 왼쪽 위부터 읽은 64글자예요. 맨 앞 8글자가 8번째 줄, 맨 뒤 8글자가 1번째 줄이에요. '
                     '흑이 둘 차례였던 판은 위아래를 뒤집어 놓아서, 대문자가 늘 둘 차례 쪽이에요. '
                     '그래서 화면에서는 대문자를 흰 편으로 그리고 흰 편이 둘 차례라고 말해도 맞아요. '
                     'y는 정답 승률(둘 차례 쪽이 이길 가능성), f는 초파리 뇌 신경망, '
                     'n은 초파리 배선을 안 쓴 보통 신경망의 답이에요.',
            'n': len(items), 'margin': MARGIN, 'fly_run': FLY, 'net_run': NET,
            'all_positions': rep.get('spread'), 'here': grade(items), 'items': items}
    path = os.path.join(VIZ, 'chess_puzzles.json')
    json.dump(data, open(path, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print(f"퍼즐 {len(items)}개 저장: viz/chess_puzzles.json ({os.path.getsize(path) / 1024:.0f} KB)")
    print(f"  이 퍼즐에서 초파리 뇌 {data['here']['fly']} · 보통 신경망 {data['here']['net']}")
