"""체스 판 780비트 → 초파리 연결체 rate RNN(T=10) → 둘 차례 쪽 승률 로짓 하나.
누가 누구와 이어졌는지와 신호 부호는 고정, 학습하는 건 연결 세기·뉴런 치우침·입력 세기·읽기뿐이다.
vals = sign * count * softplus(logw) * SCALE 이고 softplus가 항상 양수라 학습 중에 부호가 안 뒤집힌다.
대조군 C0~C4·B3을 build() 하나로 만들어 학습 쪽이 갈래를 구분하지 않게 한다.
사용: python dl/chess_net.py selftest   (뉴런 200개 가짜 그래프, 연결체 파일 없이 돈다)"""
import os, sys, time
import numpy as np, torch
import torch.nn.functional as F

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from conn_op import Conn, conn_matmul, self_test

BITS = 780                                   # 말×칸 768 + 캐슬링 4 + 앙파상 8
PARAMS = 2743380                             # C0의 학습 변수 수. C3이 이 수를 맞춘다
CHESS = os.path.join(HERE, 'chess')
# 배선 세기 손잡이. 맥에서 실제 배선·판 4개로 잰 T=10 활동(최대값): 0.01→1.1, 0.02→17, 0.03→237, 0.05→9827.
# bench_gpu가 쓰던 0.05는 속도 재려고 고른 값이라 실제 배선에서는 터진다. 갈래마다 다르게 주면 공정성이 깨지니 여기 하나만 고친다.
SCALE = 0.02


def _bg():
    """bench_gpu는 import만 해도 파케이 0.47 GB를 읽는다. 그래프가 필요한 갈래에서만 부른다"""
    import bench_gpu; return bench_gpu


def edges_table(min_syn=5):
    """시냅스 min_syn개 이상인 연결의 (보내는, 받는, 부호, log1p 시냅스수). 이 행 순서가 곧 logw 순서다"""
    con = _bg().con; e = con[con.Connectivity >= min_syn]
    return (e.Presynaptic_Index.values, e.Postsynaptic_Index.values,
            np.sign(e.Excitatory.values).astype(np.float32), np.log1p(e.Connectivity.values).astype(np.float32))


def _bad(pre, post, n):
    """자기연결이거나 (pre,post)가 앞의 것과 겹치는 자리. 중복은 CSR에서 동작이 정의돼 있지 않다"""
    key = pre.astype(np.int64) * n + post
    o = np.argsort(key, kind='stable')
    dup = np.zeros(len(key), bool); dup[o[1:]] = key[o[1:]] == key[o[:-1]]   # 뒤에 나온 중복만 표시
    return np.flatnonzero(dup | (pre == post))


def rewire(pre, post, n, seed):
    """C1: 방향 구성모형. pre를 안 건드리니 나가는 차수가, post가 순열이니 들어오는 차수가 정확히 보존된다"""
    rng = np.random.default_rng(seed)
    post2 = rng.permutation(post)
    for _ in range(30):
        bad = _bad(pre, post2, n)
        if not len(bad): break
        pool = np.unique(np.concatenate([bad, rng.integers(0, len(pre), 10 * len(bad))]))
        post2[pool] = rng.permutation(post2[pool])     # 부분집합만 다시 섞어도 전체 다중집합은 안 변한다
    assert not len(_bad(pre, post2, n)), '재배선 수리 실패: 그래프가 촘촘하면 순열 방식으로는 안 풀린다'
    assert (np.bincount(post, minlength=n) == np.bincount(post2, minlength=n)).all(), '들어오는 차수가 안 맞는다'
    return post2


def random_wire(pre, post, sign, count, n, seed):
    """C2: 같은 크기 무작위 희소망. 흥분·억제 비율과 시냅스 수 분포까지 같게 둬야 C0가 '배선'으로 이긴 게 된다"""
    rng = np.random.default_rng(seed)
    pre2 = rng.integers(0, n, len(pre)); post2 = rng.integers(0, n, len(post))
    for _ in range(30):
        bad = _bad(pre2, post2, n)
        if not len(bad): break
        pre2[bad] = rng.integers(0, n, len(bad)); post2[bad] = rng.integers(0, n, len(bad))
    assert not len(_bad(pre2, post2, n)), '무작위 배선 수리 실패'
    nsign = np.zeros(n, np.float32); nsign[pre] = sign
    assert np.array_equal(nsign[pre], sign), 'C2: 입력이 데일 법칙을 어겨서 뉴런 단위 부호표를 못 만든다'
    uniq = np.unique(pre); w = np.bincount(pre, minlength=n)[uniq].astype(float)
    # 억제 뉴런이 흥분 뉴런보다 나가는 연결이 많다(실측 26.4 대 19.3). 균등하게 뽑으면 변 수준 흥분비가 0.611이 아니라 0.681이 된다
    nsign2 = nsign[rng.choice(uniq, n, p=w / w.sum())]        # 뉴런마다 하나씩 → 데일 유지
    return pre2, post2, nsign2[pre2], rng.permutation(count)


def neurons():
    """입력 감각 뉴런과 읽기 뉴런. 시드 0 고정이라 C0·C1·C2·C4가 완전히 같은 입력 배선을 받는다.
    min_syn을 인자로 받지 않는 건 npz 캐시가 그걸 모르기 때문이다. edges_table의 기본값을 바꾸면 이 파일을 지울 것"""
    path = os.path.join(CHESS, 'neurons.npz')
    if os.path.exists(path):
        z = np.load(path); return dict(sens=z['sens'], ro=z['ro'], per=int(z['per']))
    import pandas as pd
    m = os.path.join(HERE, '..', 'model')
    comp = pd.read_csv(os.path.join(m, '2023_03_23_completeness_630_final.csv'), index_col=0)   # 이 행 순서가 뉴런 인덱스를 정의한다
    ann = pd.read_csv(os.path.join(m, 'flywire_annotations_v630.tsv'), sep='\t', low_memory=False)
    ann = ann[ann.root_id.isin(comp.index)].drop_duplicates('root_id').set_index('root_id')
    pos = {rid: i for i, rid in enumerate(comp.index)}
    pre, _, _, _ = edges_table()
    live = np.bincount(pre, minlength=_bg().N) > 0                # 나가는 연결이 없는 감각 뉴런은 넣어 봐야 아무 데도 안 간다
    sens = ann[ann.super_class == 'sensory'].index.map(pos).to_numpy().astype(np.int64)
    sens = np.random.default_rng(0).permutation(sens[live[sens]])
    per = 7
    while per > 1 and len(sens) < BITS * per: per -= 1
    assert per >= 1 and len(sens) >= BITS * per, f'감각 뉴런이 {len(sens)}개뿐이라 특징당 1개도 못 준다'
    if per != 7: print(f'감각 뉴런이 {len(sens)}개라 특징당 {per}개로 낮췄어요', flush=True)
    ro = ann[ann.super_class.isin(['descending', 'motor'])].index.map(pos).to_numpy().astype(np.int64)
    sens = sens[:BITS * per]
    os.makedirs(CHESS, exist_ok=True)
    np.savez_compressed(path + '.tmp.npz', sens=sens, ro=ro, per=per); os.replace(path + '.tmp.npz', path)
    return dict(sens=sens, ro=ro, per=per)


class FlyNet(torch.nn.Module):
    """연결 세기만 배우는 rate RNN. 배선(conn)과 부호(sign)는 버퍼라 학습 대상이 아니다"""

    def __init__(self, conn, sign, count, sens, ro, per, chunk, T=10, scale=SCALE, train_wiring=True):
        super().__init__()
        self.conn, self.chunk, self.T, self.scale = conn, chunk, T, scale
        self.per, self.train_wiring = per, train_wiring
        for k, v in dict(sign=sign, count=count, sens=sens, ro=ro).items(): self.register_buffer(k, v)
        self.logw = torch.nn.Parameter(torch.zeros(len(sign)))
        self.bias = torch.nn.Parameter(torch.zeros(conn.n))
        self.gain = torch.nn.Parameter(torch.ones(len(sens) // per))
        self.head = torch.nn.Linear(len(ro), 1)
        if not train_wiring:
            for p in (self.logw, self.bias, self.gain): p.requires_grad_(False)

    def vals(self):
        return self.sign * self.count * F.softplus(self.logw) * self.scale

    def state(self, x):
        """T단계 돌린 뒤 뉴런 활동 r [batch, n]"""
        vals = self.vals()
        with torch.set_grad_enabled(self.train_wiring and torch.is_grad_enabled()):   # 평가 때 바깥 no_grad 안에서 다시 켜지면 안 된다
            u = torch.zeros(len(x), self.conn.n, device=x.device)
            u[:, self.sens] = (x * self.gain).repeat_interleave(self.per, 1)
            r = torch.zeros_like(u)
            for _ in range(self.T):
                r = r + 0.5 * (-r + torch.relu(conn_matmul(vals, r, self.conn, self.chunk) + u + self.bias))
        return r

    def forward(self, x):
        return self.head(self.state(x)[:, self.ro]).squeeze(1)      # 로짓 하나


def init_activity(net, x):
    """T단계 다 돌린 뒤 r의 (평균, 최대). 학습 전에 찍어 폭발이나 전멸을 20시간 태우기 전에 잡는다.
    한 걸음만 보면 입력이 켜진 칸 수만 보여서 scale이 맞는지 알 수 없다. 재귀를 다 돌려야 보인다"""
    with torch.no_grad(): r = net.state(x)
    return round(float(r.mean()), 5), round(float(r.max()), 3)


def mlp(h):
    """h=0이면 판 780비트를 그대로 더하는 선형 계산(B3), 아니면 은닉층 하나짜리 보통 신경망(C3)"""
    lay = [torch.nn.Linear(BITS, 1)] if h == 0 else [torch.nn.Linear(BITS, h), torch.nn.ReLU(), torch.nn.Linear(h, 1)]
    return torch.nn.Sequential(*lay, torch.nn.Flatten(0))           # FlyNet과 같은 [batch] 모양으로 맞춘다


def hidden_for(target=PARAMS):
    """C0와 변수 수가 같아지는 은닉층 크기: 780h + h + h + 1 = 782h + 1"""
    h = (target - 1) // 782
    assert abs(782 * h + 1 - target) / target < 0.01, '변수 수가 1% 넘게 어긋난다'
    return h


def n_params(m):
    return sum(p.numel() for p in m.parameters() if p.requires_grad)


def sign_is_fixed(net):
    """학습이 끝난 뒤에도 연결 부호가 그대로인가. '신호 부호는 고정'을 말이 아니라 검사로 남긴다"""
    with torch.no_grad(): return bool((net.vals() * net.sign >= 0).all())   # 0(연결이 꺼짐)은 뒤집힌 게 아니다. NaN은 여기서 False로 걸린다


def build(arm, seed, device, batch):
    """갈래 이름 하나로 모델을 만든다. 학습 쪽에 갈래별 if 문이 안 생기게 하는 게 이 함수의 전부다"""
    if arm not in ('C0', 'C1', 'C2', 'C3', 'C4', 'B3'): sys.exit(f'모르는 갈래예요: {arm}')
    torch.manual_seed(seed)
    info = dict(arm=arm, seed=seed, batch=batch, edges=None, T=None, chunk=None, per=None, scale=None,
                dead_readout=None, rewire_seconds=None, self_loops=None, duplicates=None)
    if arm in ('B3', 'C3'):
        m = mlp(0 if arm == 'B3' else hidden_for()).to(device)
        info['n_params'] = n_params(m)
        if arm == 'C3': assert abs(info['n_params'] - PARAMS) / PARAMS < 0.01, info
        return m, info
    bg = _bg(); pre, post, sign, count = edges_table()
    t0 = time.time()
    if arm == 'C1': post = rewire(pre, post, bg.N, seed)
    elif arm == 'C2': pre, post, sign, count = random_wire(pre, post, sign, count, bg.N, seed)
    info['rewire_seconds'] = round(time.time() - t0, 1)
    key = pre.astype(np.int64) * bg.N + post
    info['self_loops'] = int((pre == post).sum()); info['duplicates'] = len(key) - len(np.unique(key))
    assert info['self_loops'] == 0 and info['duplicates'] == 0, info   # 셋이 같은 조건이어야 비교가 산다
    nr = neurons()
    t = lambda a, d: torch.as_tensor(a, dtype=d, device=device)
    m = FlyNet(Conn(pre, post, bg.N, device), t(sign, torch.float32), t(count, torch.float32),
               t(nr['sens'], torch.long), t(nr['ro'], torch.long), nr['per'],
               bg.chunk_for(len(pre), batch), train_wiring=(arm != 'C4')).to(device)
    info.update(edges=len(pre), T=m.T, chunk=m.chunk, per=m.per, scale=m.scale, n_params=n_params(m),
                dead_readout=int((np.bincount(post, minlength=bg.N)[nr['ro']] == 0).sum()))
    assert info['n_params'] == PARAMS or arm == 'C4', info   # 배선 갈래는 정의상 변수 수가 같다. C3이 맞추는 수이기도 하다
    return m, info


if __name__ == '__main__':
    assert self_test('cpu'), 'conn_op 기울기 불일치'
    torch.manual_seed(0)               # head 초기값까지 고정해야 아래 손실 검사가 안 흔들린다
    n, bits, per = 200, 20, 2          # 뉴런 60개면 연결 400개가 밀도 11%라 재배선이 안 풀린다 (실제는 0.016%)
    rng = np.random.default_rng(0)
    key = np.unique(rng.integers(0, n * n, 600)); key = key[(key // n) != (key % n)][:400]
    pre, post = (key % n).astype(np.int64), (key // n).astype(np.int64)
    nsign = rng.choice([-1.0, 1.0], n).astype(np.float32)          # 데일 법칙: 뉴런마다 부호 하나
    sign, count = nsign[pre], np.log1p(rng.integers(5, 50, len(pre))).astype(np.float32)
    assert not len(_bad(pre, post, n)), '가짜 그래프부터 더럽다'

    post2 = rewire(pre, post, n, 7)
    assert (np.bincount(post, minlength=n) == np.bincount(post2, minlength=n)).all(), '들어오는 차수가 안 맞는다'
    assert not len(_bad(pre, post2, n)) and (post2 != post).mean() > 0.5, '섞이지 않았다'
    p2, q2, s2, c2 = random_wire(pre, post, sign, count, n, 7)
    assert len(p2) == len(pre) and not len(_bad(p2, q2, n))
    assert sorted(c2.tolist()) == sorted(count.tolist()), '시냅스 수 다중집합이 안 보존됐다'
    assert all(len(np.unique(s2[p2 == u])) == 1 for u in np.unique(p2)), 'C2에서 데일 법칙이 깨졌다'
    bp = np.repeat(np.arange(20), [1] * 10 + [9] * 10)             # 억제 뉴런(10~19)이 9배 많이 보내는 가짜 그래프
    bq = (np.arange(len(bp)) + 20) % 100; keep = bp != bq; bp, bq = bp[keep], bq[keep]
    bs = np.where(bp < 10, 1.0, -1.0).astype(np.float32); bc = np.ones(len(bp), np.float32)
    got = np.mean([(random_wire(bp, bq, bs, bc, 100, s)[2] > 0).mean() for s in range(20)])
    assert abs(got - (bs > 0).mean()) < 0.03, (got, (bs > 0).mean())   # 뉴런 수 기준(0.5)이 아니라 변 수준(0.1) 흥분비가 나와야 한다

    conn = Conn(pre, post, n, 'cpu')
    ro = torch.as_tensor(np.argsort(-np.bincount(post, minlength=n))[:10].copy())   # 들어오는 연결이 0인 뉴런을 읽으면 배울 게 없다
    mk = lambda tw: FlyNet(conn, torch.tensor(sign), torch.tensor(count), torch.arange(bits * per),
                           ro, per, chunk=4, T=4, scale=0.5, train_wiring=tw)
    x = torch.tensor(rng.integers(0, 2, (16, bits)), dtype=torch.float32)
    y = torch.sigmoid(x @ torch.tensor(rng.normal(size=bits), dtype=torch.float32))   # 배울 게 있는 가짜 정답
    m = mk(True); a0, amax = init_activity(m, x)
    assert 0 < a0 < 1e3 and np.isfinite(amax), f'학습 전 활동이 이상해요: 평균 {a0} 최대 {amax}'
    ev = lambda: float(F.binary_cross_entropy_with_logits(m(x), y).detach())
    opt = torch.optim.AdamW(m.parameters(), lr=0.05)
    l0 = ev()
    for _ in range(20):
        loss = F.binary_cross_entropy_with_logits(m(x), y)
        opt.zero_grad(set_to_none=True); loss.backward(); opt.step()
    l1 = ev()
    assert all(torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0 for p in (m.logw, m.bias, m.gain)), '배선 쪽으로 기울기가 안 간다'
    assert l1 < l0 * 0.9, (l0, l1)
    assert sign_is_fixed(m), '학습 중에 부호가 뒤집혔다'

    c4 = mk(False); c4(x).sum().backward()
    assert n_params(c4) == 11 and c4.logw.grad is None and c4.head.bias.grad is not None, 'C4가 배선까지 학습한다'

    assert hidden_for() == 3508 and abs(n_params(mlp(3508)) - PARAMS) / PARAMS < 0.01
    assert n_params(mlp(0)) == 781 and mlp(0)(torch.zeros(3, BITS)).shape == (3,)
    mb, ib = build('B3', 1, 'cpu', 32)
    assert ib['n_params'] == 781 and 'bench_gpu' not in sys.modules, 'B3가 연결체 파케이를 읽었다'
    mc, ic = build('C3', 3, 'cpu', 32)
    assert abs(ic['n_params'] - PARAMS) / PARAMS < 0.01, ic
    print(f'selftest ok | 손실 {l0:.4f} → {l1:.4f} | 학습 전 활동 평균 {a0} 최대 {amax} | 은닉 {hidden_for()}'
          f' | 변수 C3 {ic["n_params"]} vs C0 {PARAMS}')
    sys.exit()
