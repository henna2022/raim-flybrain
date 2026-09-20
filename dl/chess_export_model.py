"""학습된 체스 신경망을 브라우저가 읽을 수 있는 이진 파일로 바꾼다.
태블릿은 이 파일로 판마다 신경망을 직접 돌린다(체스는 미리 계산해 둘 수 없다).
연결 세기는 vals = 부호 x 시냅스수 x softplus(logw) x SCALE 을 미리 곱해 하나로 합쳐 둔다.
CSR 순서는 conn_op.Conn 과 똑같이 (받는 뉴런, 보내는 뉴런) 정렬이어야 한다.
산출: viz/net/{vals,col,crow,bias,gain,sens,ro,head}.bin 과 net.json
사용: python dl/chess_export_model.py dl/chess/runs/C0_s1.pt
      python dl/chess_export_model.py --verify   (내보낸 값으로 파이썬 예측을 재현해 본다)
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'viz', 'net')
N, MIN_SYN = 127400, 5


def tables(ckpt):
    """체크포인트와 연결체에서 브라우저가 쓸 배열들을 만든다"""
    import torch
    sys.path.insert(0, HERE)
    import chess_net
    d = torch.load(ckpt, map_location='cpu')
    m = d['model']
    pre, post, sign, count = chess_net.edges_table(MIN_SYN)
    assert len(pre) == len(m['logw']), (len(pre), len(m['logw']))
    assert np.allclose(sign, m['sign'].numpy()) and np.allclose(count, m['count'].numpy()), '연결 순서가 학습 때와 다릅니다'

    vals = (m['sign'] * m['count'] * torch.nn.functional.softplus(m['logw']) * chess_net.SCALE).numpy()
    order = np.argsort(post.astype(np.int64) * N + pre, kind='stable')          # conn_op.Conn._csr 과 같은 순서
    crow = np.zeros(N + 1, np.int64)
    crow[1:] = np.bincount(post, minlength=N).cumsum()
    return dict(vals=vals[order].astype(np.float32), col=pre[order].astype(np.int32),
                crow=crow.astype(np.int32), bias=m['bias'].numpy().astype(np.float32),
                gain=m['gain'].numpy().astype(np.float32), sens=m['sens'].numpy().astype(np.int32),
                ro=m['ro'].numpy().astype(np.int32),
                head=np.concatenate([m['head.weight'].numpy().ravel(), m['head.bias'].numpy().ravel()]).astype(np.float32)), d


def neuron_points(ckpt_model, sample=0.25, seed=5):
    """뇌 그림용 점: (뉴런 번호, 화면 좌표 x·y, 종류). 종류 0 배경 · 1 감각 · 2 읽기.
    좌표 규칙은 틱택토 화면(model/ttt_build_ui.py)과 같게 ±1000 으로 맞춘다."""
    import pandas as pd
    M = os.path.join(HERE, '..', 'model')
    comp = pd.read_csv(os.path.join(M, '2023_03_23_completeness_630_final.csv'), index_col=0)
    ann = pd.read_csv(os.path.join(M, 'flywire_annotations_v630.tsv'), sep='\t', low_memory=False)
    ann = ann[ann.root_id.isin(comp.index)].drop_duplicates('root_id').set_index('root_id')
    pos = {rid: i for i, rid in enumerate(comp.index)}
    idx = ann.index.map(pos).to_numpy()                      # 좌표가 있는 뉴런의 번호
    xy = ann[['pos_x', 'pos_y']].to_numpy(float)
    center, scale = (xy.min(0) + xy.max(0)) / 2, (xy.max(0) - xy.min(0)).max() / 2
    xy = np.round((xy - center) / scale * 1000).astype(np.int16)

    kind = np.zeros(len(idx), np.uint8)
    sens, ro = set(ckpt_model['sens'].tolist()), set(ckpt_model['ro'].tolist())
    for j, i in enumerate(idx):
        if i in ro: kind[j] = 2
        elif i in sens: kind[j] = 1
    keep = (kind > 0) | (np.random.default_rng(seed).random(len(idx)) < sample)
    return idx[keep].astype(np.int32), xy[keep], kind[keep]


def forward(t, x, T=10):
    """브라우저에서 돌릴 것과 같은 계산을 넘파이로. 검증용이라 느려도 된다"""
    per = len(t['sens']) // len(t['gain'])
    u = np.zeros(N, np.float32)
    u[t['sens']] = np.repeat(x * t['gain'], per)
    u += t['bias']
    r = np.zeros(N, np.float32)
    col, crow, vals = t['col'], t['crow'], t['vals']
    for _ in range(T):
        wr = np.add.reduceat(vals * r[col], crow[:-1]) * (np.diff(crow) > 0)     # 빈 행은 0
        r = r + 0.5 * (-r + np.maximum(wr + u, 0))
    z = float(r[t['ro']] @ t['head'][:-1] + t['head'][-1])
    return 1 / (1 + np.exp(-z))


def bits_of(row):
    return np.unpackbits(row)[:780].astype(np.float32)


if __name__ == '__main__':
    if sys.argv[1:2] == ['--verify']:
        import torch
        t = {k: np.fromfile(os.path.join(OUT, k + '.bin'),
                            dtype=np.int32 if k in ('col', 'crow', 'sens', 'ro') else np.float32)
             for k in ('vals', 'col', 'crow', 'bias', 'gain', 'sens', 'ro', 'head')}
        z = np.load(os.path.join(HERE, 'chess', 'val.npz'))
        want = np.load(os.path.join(HERE, 'chess', 'runs', 'C0_s1_val.npy'))
        err = []
        for i in range(12):
            got = forward(t, bits_of(z['bits'][i]))
            err.append(abs(got - float(want[i])))
            print(f'  {i:2d}번 판  파이썬 {want[i]:.4f}  내보낸값 {got:.4f}  차이 {err[-1]:.6f}')
        assert max(err) < 2e-3, f'예측이 재현되지 않습니다 (최대 차이 {max(err)})'
        print(f'검증 통과 | 12판 최대 차이 {max(err):.6f}')
        sys.exit()

    ckpt = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'chess', 'runs', 'C0_s1.pt')
    t, d = tables(ckpt)
    import torch; torch_model = torch.load(ckpt, map_location='cpu')['model']
    os.makedirs(OUT, exist_ok=True)
    for k, v in t.items():
        v.tofile(os.path.join(OUT, k + '.bin'))
    nidx, nxy, nkind = neuron_points(torch_model)
    nidx.tofile(os.path.join(OUT, 'npt_idx.bin')); nxy.tofile(os.path.join(OUT, 'npt_xy.bin'))
    nkind.tofile(os.path.join(OUT, 'npt_kind.bin'))
    meta = dict(n=N, edges=int(len(t['vals'])), T=int(d['T']), per=int(len(t['sens']) // len(t['gain'])),
                points=int(len(nidx)), points_sens=int((nkind == 1).sum()), points_ro=int((nkind == 2).sum()),
                bits=int(len(t['gain'])), readout=int(len(t['ro'])), seed=int(d['seed']),
                positions=int(d['positions']), step=int(d['step']),
                _note='vals 에 부호·시냅스수·SCALE 이 이미 곱해져 있어요. r=0에서 시작해 '
                      'r += 0.5*(-r + relu(W r + u + bias)) 를 T번 돌리고, 읽기 뉴런에 head 를 곱해 시그모이드 하면 승률이에요.')
    json.dump(meta, open(os.path.join(OUT, 'net.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    total = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT))
    print(json.dumps(meta, ensure_ascii=False)[:160])
    for k in t: print(f'  {k}.bin {os.path.getsize(os.path.join(OUT, k + ".bin")) / 2**20:6.2f} MB')
    print(f'합계 {total / 2**20:.1f} MB')
