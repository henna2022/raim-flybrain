"""대조군 C0~C4·B3을 똑같은 조건으로 학습해 한 표에 모으고 관문을 판정한다.
데이터·걸음 수·배치 크기·학습률이 전부 같고, 씨앗은 초기값·배선 섞기·배치 순서에만 쓴다.
같은 씨앗끼리는 배치 순서까지 같으니 갈래 사이 비교는 그대로고, 씨앗 사이 산포는 진짜 산포가 된다.
끊겨도 그대로 다시 실행하면 이어서 한다.
산출: dl/chess/runs/{태그}.json·.pt·_val.npy, dl/chess/report.json
사용: python dl/chess_train.py all        (12개 런 전부, 이어받기)
      python dl/chess_train.py C0 2       (하나만)
      python dl/chess_train.py report     (끝난 런들로 관문 판정만)
      python dl/chess_train.py selftest   (가짜 지표로 채점·관문 확인, 파일도 torch도 없이 돈다)"""
import functools, json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'chess')
RUNS = os.path.join(OUT, 'runs')

# 아래 상수를 건드리면 갈래끼리 비교가 무효가 된다. 바꿨으면 모든 런을 처음부터 다시 돌려야 한다.
# 바닥 갈래(B3·C4·C3)를 먼저 돌린다. 중간에 끊겨도 관문의 바닥이 먼저 확보돼 있어야 한다
ARMS = {'B3': (1,), 'C4': (1,), 'C3': (3,), 'C0': (1, 2, 3), 'C1': (1, 2, 3), 'C2': (1, 2, 3)}
BATCH, T, LR, POSITIONS, SAVE_EVERY = 128, 10, 1e-3, 500_000, 200
DATA_SEED = 0                     # 배치 순서는 같은 시드끼리만 공유한다 (갈래 사이 비교는 시드를 맞춰서 본다)
K = 'better_side_agree'           # 주 지표를 미리 못 박는다. 결과를 보고 고르면 사후 선택이다
MARGIN = 0.05                     # |승률 - 0.5| >= 0.05 인 판만 본다 (약 55 센티폰, 어느 쪽이 유리한지 뚜렷한 판)
spread = lambda xs: (lambda s: {'min': s[0], 'median': s[len(s) // 2], 'max': s[-1], 'n': len(s)})(sorted(xs))
mean = lambda xs: round(float(np.mean(xs)), 4)
# 시간 예산: 연결망 역전파가 도는 건 9런(C0·C1·C2 x 3시드). 시간 = 국면수 x 9 / P / 3600
#   50만: P=50 → 25h, P=100 → 12.5h, P=200 → 6.3h   200만: 100h / 50h / 25h   (맥 CPU 실측 P=7.1이라 맥에서는 불가)


@functools.lru_cache(maxsize=1)
def data():
    """chess_data.py가 만든 학습·검증 판을 한 번만 읽는다"""
    if not os.path.exists(os.path.join(OUT, 'train.npz')):
        sys.exit('dl/chess/train.npz가 없어요. 먼저 python dl/chess_data.py 500000 을 돌려 주세요')
    z = [np.load(os.path.join(OUT, n)) for n in ('train.npz', 'val.npz')]
    return z[0]['bits'], z[0]['y'].astype(np.float32), z[1]['bits'], z[1]['y'].astype(np.float32)


def batch_idx(n, step, seed):
    """걸음 번호와 씨앗만으로 정해지는 표본. 상태가 없어서 이어받기가 이 한 줄로 끝난다.
    씨앗을 넣는 이유: C0는 logw·bias·gain이 전부 상수 초기값이라 이게 없으면 세 씨앗이 같은 런이 된다"""
    return np.random.default_rng([DATA_SEED, seed, step]).integers(n, size=BATCH)


def unpack(bits):
    return np.unpackbits(bits, axis=1)[:, :780].astype(np.float32)


def batch_of(bits, y, step, device, seed):
    import torch
    idx = batch_idx(len(y), step, seed)
    return torch.from_numpy(unpack(bits[idx])).to(device), torch.from_numpy(y[idx]).to(device)


def scores(preds, y):
    """K는 정확도라 '차이 1% 이상'이 그대로 0.01이 된다. op_train의 best_move_where_choice_matters와 같은 자리"""
    m = np.abs(y - 0.5) >= MARGIN
    p = np.clip(preds, 1e-6, 1 - 1e-6)
    f = float((y[m] > 0.5).mean()) if m.any() else 0.5
    return {K: mean((preds[m] > 0.5) == (y[m] > 0.5)), 'better_side_agree_all': mean((preds > 0.5) == (y > 0.5)),
            'val_mae': mean(np.abs(preds - y)), 'val_bce': mean(-(y * np.log(p) + (1 - y) * np.log(1 - p))),
            'majority': mean(max(f, 1 - f)),   # 한쪽으로만 외치는 모델이 그냥 받는 점수. 이걸 못 넘으면 아무것도 안 배운 것이다
            'n_val': int(len(y)), 'n_decisive': int(m.sum())}


def correct_of(preds, y):
    """관문 짝 비교용: 뚜렷한 판에서 유리한 쪽을 맞혔나 0/1"""
    m = np.abs(y - 0.5) >= MARGIN
    return ((preds[m] > 0.5) == (y[m] > 0.5)).astype(float)


def boot_ci(a, b, n=1000):
    """같은 검증 판에 대한 0/1 두 개를 국면 인덱스로 짝지어 다시 뽑는다. 짝지어야 짝 비교가 된다"""
    a, b = np.asarray(a, float), np.asarray(b, float)
    assert len(a) == len(b), '같은 검증 집합이 아니면 짝 비교가 안 된다'
    rng = np.random.default_rng(11)
    d = [a[i].mean() - b[i].mean() for i in (rng.integers(len(a), size=len(a)) for _ in range(n))]
    return round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)


def gate_from(runs, majority=0.5):
    """runs: [{'arm', K, 'correct'}]. 평균이 아니라 최대값으로 판정한다 (op_train 관문과 같은 형태)"""
    pick = lambda arm: [r for r in runs if r['arm'] == arm]
    c0, c1 = pick('C0'), pick('C1')
    if not c0 or not c1: sys.exit('C0 또는 C1 런이 없어서 관문을 판정할 수 없어요')
    k0, k1 = [r[K] for r in c0], [r[K] for r in c1]
    # 바닥: 판 비트를 그냥 더한 것(B3) · 읽기만 학습한 것(C4) · 한쪽으로만 외치기(다수결). 바닥 갈래가 없으면 관문 자체가 성립하지 않는다
    floor = max([r[K] for r in pick('B3') + pick('C4')] + [majority])
    lo, hi = boot_ci(min(c0, key=lambda r: r[K])['correct'], max(c1, key=lambda r: r[K])['correct'])
    gate = {'g0_floor_arms_present': bool(pick('B3') and pick('C4')),
            'g1_C0_min_beats_C1_max': min(k0) > max(k1),
            'g2_gap_ge_0.01': round(min(k0) - max(k1), 4) >= 0.01,
            'g3_paired_ci_above_0': lo > 0,
            'g4_above_floor': round(min(k0) - floor, 4) >= 0.01,
            'g5_three_seeds_each': len(k0) >= 3 and len(k1) >= 3}
    gate['pass'] = all(gate.values())
    gate['_전시_문구_허용'] = gate['pass']                                # "섞은 배선보다 조금 더 잘 맞혔어요"
    gate['paired_ci_worst_C0_minus_best_C1'] = [lo, hi]                 # all() 다음에 넣는다
    gate['floor'] = floor; gate['majority'] = majority
    return gate


def evaluate(model, bits, y, device):
    """검증 판 전체를 BATCH씩 돌려 지표와 국면별 예측을 낸다"""
    import torch
    out = []
    with torch.no_grad():
        for i in range(0, len(y), BATCH):
            x = torch.from_numpy(unpack(bits[i:i + BATCH])).to(device)
            out.append(torch.sigmoid(model(x)).float().cpu().numpy())
    preds = np.concatenate(out).astype(np.float32)
    return scores(preds, y), preds


def save_ckpt(path, model, opt, step, seed, positions):
    import torch
    torch.save({'model': model.state_dict(), 'opt': opt.state_dict(), 'step': step, 'batch': BATCH,
                'T': T, 'positions': positions, 'lr': LR, 'seed': seed}, path + '.tmp')
    os.replace(path + '.tmp', path)


def train_one(arm, seed, positions, device):
    import torch
    sys.path.insert(0, HERE)
    import chess_net
    from conn_op import self_test
    tag = f'{arm}_s{seed}'
    rec_path = os.path.join(RUNS, tag + '.json')
    if os.path.exists(rec_path):
        r = json.load(open(rec_path, encoding='utf-8'))
        if r.get('done'): print(f'{tag}: 이미 끝났어요', flush=True); return r
    assert self_test(device), 'conn_matmul 기울기가 밀집 autograd와 달라요. 이대로 학습하면 안 됩니다'
    os.makedirs(RUNS, exist_ok=True)
    bits, y, vbits, vy = data()
    model, info = chess_net.build(arm, seed, device, BATCH)
    edges = int(info['edges'] or 0)                                     # 배선이 없는 갈래(C3·B3)는 None으로 온다
    if edges:
        assert info['T'] == T, f'chess_net의 T={info["T"]}와 여기 T={T}가 다릅니다'   # 상수가 두 파일에 있어서 갈라질 수 있다
        from bench_gpu import chunk_for, est_gib, ram_gib, vram        # import만 해도 파케이 0.47 GB를 읽어서 배선 갈래에서만 부른다
        need = est_gib(BATCH, T, edges, chunk_for(edges, BATCH))
        limit = 0.8 * vram if device == 'cuda' else 0.6 * ram_gib()     # CPU에서 모자라면 리눅스가 경고 없이 죽인다
        if need > limit:                                                # 갈래마다 배치가 달라지면 비교가 무효라 전부 중단한다
            sys.exit(f'배치 {BATCH}이 안 들어가요 (약 {need:.1f} GiB 필요, 한도 {limit:.1f} GiB). BATCH를 낮추고 모든 갈래를 처음부터 다시 돌려 주세요')
    params = [p for p in model.parameters() if p.requires_grad]         # 얼린 logw는 옵티마이저에 넣지 않는다 (Adam 상태 21 MB가 헛되이 잡힌다)
    opt = torch.optim.AdamW(params, lr=LR)
    steps, step, ckpt = positions // BATCH, 0, os.path.join(RUNS, tag + '.pt')
    if os.path.exists(ckpt):
        s = torch.load(ckpt, map_location=device)
        if (s['batch'], s['T'], s['positions'], s['lr']) != (BATCH, T, positions, LR):
            sys.exit(f'{tag}: 체크포인트 조건({s["batch"]}, {s["T"]}, {s["positions"]}, {s["lr"]})이 지금 상수와 달라요. 이어서 하면 비교가 무효입니다')
        model.load_state_dict(s['model']); opt.load_state_dict(s['opt']); step = s['step']
        print(f'{tag}: {step}/{steps} 걸음부터 이어서 합니다', flush=True)
    elif edges:                                                         # 시작할 때 폭발·전멸인지 한 번 찍어 둔다 (MLP 갈래는 state()가 없다)
        act = chess_net.init_activity(model, batch_of(bits, y, 0, device, seed)[0])   # (평균, 최대)
        info['init_activity'] = list(act)
        if not (0 < act[0] < 1e3 and np.isfinite(act[1])):              # 20시간 태우기 전에 여기서 잡는다
            sys.exit(f'{tag}: 학습 전 활동이 이상해요 (평균 {act[0]}, 최대 {act[1]}). chess_net.SCALE을 고치고 다시 돌려 주세요')
    t0 = time.time()
    while step < steps:                                                 # 조기 종료도 최적 지점 되돌리기도 없다. 걸음 수가 같은 게 공정성이다
        x, t = batch_of(bits, y, step, device, seed)
        loss = torch.nn.functional.binary_cross_entropy_with_logits(model(x), t)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(params, 1.0)                     # T=10 펼친 RNN이라 없으면 긴 런을 통째로 날린다
        opt.step(); opt.zero_grad(set_to_none=True); step += 1
        if step % 100 == 0:                                             # .item()은 GPU 동기화라 출력할 때만 본다
            l = loss.item(); print(f'{tag} {step}/{steps} loss {l:.4f} {(time.time() - t0) / 60:.1f}분', flush=True)
            if not np.isfinite(l): sys.exit(f'{tag}: {step}걸음에서 손실이 {l}이 됐어요. 학습률이나 chess_net.SCALE을 낮추고 이 런의 .pt를 지운 뒤 다시 돌려 주세요')
        if step % SAVE_EVERY == 0 or step == steps: save_ckpt(ckpt, model, opt, step, seed, positions)
    metrics, preds = evaluate(model, vbits, vy, device)
    assert np.isfinite(preds).all(), f'{tag}: 예측에 NaN이 있어요. 학습이 중간에 터졌습니다'
    np.save(os.path.join(RUNS, tag + '_val.tmp.npy'), preds)
    os.replace(os.path.join(RUNS, tag + '_val.tmp.npy'), os.path.join(RUNS, tag + '_val.npy'))
    sign_fixed = chess_net.sign_is_fixed(model) if edges else None      # 배선 부호가 학습 중에 안 뒤집혔나 (MLP 갈래는 볼 게 없다)
    assert sign_fixed is not False, f'{tag}: 배선 부호가 뒤집혔어요. sign * softplus 구조가 깨졌습니다'
    rec = dict(tag=tag, arm=arm, seed=seed, n_params=info['n_params'], edges=edges,
               steps=steps, batch=BATCH, T=T, positions=positions, lr=LR, metrics=metrics,
               minutes=round((time.time() - t0) / 60, 1), device=device, sign_fixed=sign_fixed, info=info, done=True)
    json.dump(rec, open(rec_path + '.tmp', 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    os.replace(rec_path + '.tmp', rec_path)
    print(tag, metrics, flush=True)
    return rec


def report():
    """끝난 런들을 한 표로 모아 관문을 판정한다"""
    runs = [json.load(open(os.path.join(RUNS, f), encoding='utf-8'))
            for f in sorted(os.listdir(RUNS)) if f.endswith('.json')] if os.path.isdir(RUNS) else []
    runs = [r for r in runs if r.get('done')]
    if not runs: sys.exit('끝난 런이 없어요. 먼저 python dl/chess_train.py all 을 돌려 주세요')
    cond = {(r['batch'], r['T'], r['positions'], r['lr'], r['metrics']['n_val']) for r in runs}
    if len(cond) > 1: sys.exit(f'런마다 조건이 달라서 비교할 수 없어요: {sorted(cond)}')   # 대여 GPU에서 한 갈래만 큰 배치로 돌린 경우
    vy = data()[3]
    if runs[0]['metrics']['n_val'] != len(vy):
        sys.exit('지금 val.npz가 런을 돌릴 때와 달라요. dl/chess/runs를 지우고 다시 학습하거나 예전 val.npz를 되돌려 주세요')
    for r in runs:                                                      # MARGIN을 바꿨으면 저장된 지표가 아니라 예측에서 다시 매긴다
        p = np.load(os.path.join(RUNS, r['tag'] + '_val.npy'))
        r['metrics'] = scores(p, vy); r[K] = r['metrics'][K]; r['correct'] = correct_of(p, vy)
    meta = os.path.join(OUT, 'meta.json')
    rep = {'_note': ('C0 실제 배선 · C1 차수 보존 재배선 · C2 같은 크기 무작위 희소망 · C3 같은 변수 수 MLP · '
                     'C4 읽기만 학습 · B3 판 780비트 선형. 모든 런이 같은 데이터·같은 걸음 수로 돌았고, 같은 씨앗끼리는 배치 순서까지 같다. '
                     f'주 지표 {K}는 |승률-0.5| >= {MARGIN}인 판에서 어느 쪽이 유리한지를 맞힌 비율이고, '
                     'gate.majority는 한쪽으로만 외치는 모델이 그냥 받는 점수라 그 위로 올라야 뭔가 배운 것이다. '
                     '절대 수치는 라이체스 파케이 미러 샤드 하나의 행그룹 몇 개에서 뽑은 표본이고 depth>=20으로 이미 걸러진 국면이다. '
                     '갈래 사이 비교는 같은 데이터라 유효하지만, 밖에 말할 때는 이 표본 조건을 같이 적어야 한다. '
                     '검증은 학습에 안 쓴 행그룹에서 통째로 뽑아 한 대국의 이웃 국면이 양쪽에 걸치지 않게 했다. '
                     '학습 표본은 복원추출이라 positions는 뽑은 횟수다. 학습 판 수가 positions와 같으면 실제로 본 서로 다른 판은 그 63% 정도다. '
                     'arms.init_activity는 학습 전 뉴런 활동 (평균, 최대)이다. C0와 C1·C2는 이 값이 10배쯤 다르니 '
                     'C0가 이겼을 때 그게 배선 때문인지 활동 범위 때문인지는 이 숫자를 같이 놓고 봐야 한다.'),
           'margin': MARGIN, 'metric': K,
           'data': json.load(open(meta, encoding='utf-8')) if os.path.exists(meta) else {},
           'arms': {a: {'n_params': next(r['n_params'] for r in runs if r['arm'] == a),
                        'init_activity': next((r['info'].get('init_activity') for r in runs
                                               if r['arm'] == a and r['info'].get('init_activity')), None),
                        'seeds': {str(r['seed']): r['metrics'] for r in runs if r['arm'] == a}}
                    for a in ARMS if any(r['arm'] == a for r in runs)},
           'spread': {a: spread([r[K] for r in runs if r['arm'] == a]) for a in ARMS if any(r['arm'] == a for r in runs)},
           'gate': gate_from(runs, runs[0]['metrics']['majority']),
           'notes': ['관문은 평균이 아니라 C0 최소값 > C1 최대값으로 본다', '모든 런의 배치·T·국면 수·학습률·검증 판 수가 같은지 먼저 확인했다']}
    json.dump(rep, open(os.path.join(OUT, 'report.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return rep


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a or a[:1] == ['selftest']:                                  # 인자 없이 돌리면 자체 검사 (기본 동작이 될 만한 게 없다)
        rng = np.random.default_rng(5)
        y = rng.random(2000).astype(np.float32)
        s = scores(np.clip(y + rng.normal(0, .01, 2000), 0, 1), y)      # 양성: 정답을 흘린 예측이면 주 지표가 높아야 한다
        assert s[K] > 0.95, s
        s2 = scores(rng.random(2000), y)                                # 음성: 난수 예측이면 반반이어야 한다
        assert 0.45 < s2[K] < 0.55, s2
        arm_of = lambda ks, arm: [{'arm': arm, K: k, 'correct': (np.arange(2000) < round(k * 2000)).astype(float)} for k in ks]
        mix = lambda k0, k1, fl=0.55: arm_of(k0, 'C0') + arm_of(k1, 'C1') + arm_of([fl], 'B3') + arm_of([fl - 0.01], 'C4')
        assert gate_from(mix([0.60, 0.61, 0.62], [0.61, 0.59, 0.58]))['pass'] is False   # 대조군 최대값을 못 이기면 떨어진다
        assert gate_from(mix([0.63, 0.64, 0.65], [0.60, 0.59, 0.58]))['pass'] is True
        assert gate_from(mix([0.605, 0.61, 0.62], [0.60, 0.59, 0.58]))['g2_gap_ge_0.01'] is False   # 차이 1% 미만
        assert gate_from(mix([0.63, 0.64, 0.65], [0.60, 0.59, 0.58], fl=0.625))['g4_above_floor'] is False
        assert gate_from(mix([0.63, 0.64], [0.60, 0.59, 0.58]))['g5_three_seeds_each'] is False
        assert gate_from(mix([0.63, 0.64, 0.65], [0.60, 0.59, 0.58]), majority=0.63)['g4_above_floor'] is False  # 다수결도 바닥이다
        bare = arm_of([0.63, 0.64, 0.65], 'C0') + arm_of([0.60, 0.59, 0.58], 'C1')
        assert gate_from(bare)['g0_floor_arms_present'] is False and gate_from(bare)['pass'] is False   # 바닥 갈래 없이 통과하면 안 된다
        c = arm_of([0.6], 'C0')[0]['correct']
        lo, hi = boot_ci(c, c); assert lo <= 0 <= hi, (lo, hi)          # 같은 배열끼리는 구간이 0을 포함한다
        assert (batch_idx(1000, 7, 1) == batch_idx(1000, 7, 1)).all(), '같은 걸음이면 같은 판이어야 이어받기가 된다'
        assert not (batch_idx(1000, 7, 1) == batch_idx(1000, 8, 1)).all()
        assert not (batch_idx(1000, 7, 1) == batch_idx(1000, 7, 2)).all(), '씨앗이 다르면 배치 순서도 달라야 한다'
        try:
            import torch
        except ImportError:
            print('selftest ok | 라벨 흘림', s[K], '| 난수', s2[K], '| 관문 ok | torch가 없어 이어받기 검사는 건너뜀'); sys.exit()
        os.makedirs(RUNS, exist_ok=True)
        m = torch.nn.Linear(4, 1); p = os.path.join(RUNS, '_selftest.pt')
        save_ckpt(p, m, torch.optim.AdamW(m.parameters(), lr=LR), 100, 9, POSITIONS)
        st = torch.load(p, map_location='cpu'); os.remove(p)
        assert st['step'] == 100 and st['batch'] == BATCH and torch.equal(st['model']['weight'], m.weight), st['step']
        fb = np.packbits((rng.random((50, 784)) > .9).astype(np.uint8), axis=1)
        assert (batch_of(fb, y[:50], 7, 'cpu', 1)[0] == batch_of(fb, y[:50], 7, 'cpu', 1)[0]).all()
        print('selftest ok | 라벨 흘림', s[K], '| 난수', s2[K], '| 관문 ok | 이어받기 일치'); sys.exit()
    if a[:1] == ['report']:
        report(); sys.exit()
    if a[:1] != ['all'] and not (len(a) == 2 and a[0] in ARMS and a[1].isdigit() and int(a[1]) in ARMS[a[0]]):
        sys.exit(__doc__)
    import torch
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    if a[0] == 'all':
        for arm, seeds in ARMS.items():
            for sd in seeds: train_one(arm, sd, POSITIONS, dev)
        report()
    else:
        train_one(a[0], int(a[1]), POSITIONS, dev)
