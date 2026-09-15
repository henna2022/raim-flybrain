"""틱택토 태블릿 화면 viz/ttt.html 빌드. 뇌 점 위치, 판별 출력 뉴런 발화 수, 판독기 가중치를 HTML 안에 넣는다.
ttt/readout.json(ttt_train.py 산출)이 없거나 시뮬이 덜 끝났으면 있는 판만으로 임시 판독기를 만들고 '개발용'으로 표시한다."""
import json, base64, os, numpy as np
from ttt_game import candidates, value
from ttt_layout import select

b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
L = select(); ann, comp = L['ann'], L['comp']
xy = ann[['pos_x', 'pos_y']].to_numpy(float)
center, scale = (xy.min(0) + xy.max(0)) / 2, (xy.max(0) - xy.min(0)).max() / 2
to_i16 = lambda ids: np.round((ann.loc[ids, ['pos_x', 'pos_y']].to_numpy(float) - center) / scale * 1000).astype(np.int16)
sens_ids, ro_ids = comp.index[L['sens']], L['readout_ids']
rest = ann.index.difference(sens_ids).difference(ro_ids)
bg_ids = rest[np.random.default_rng(5).random(len(rest)) < 0.25]      # 배경은 25% 표본이면 뇌 모양이 충분히 보인다

C = candidates()
z = np.load('ttt/features_seed0.npz'); feats = dict(zip(z['boards'], z['X']))
have = np.array([b in feats for b in C])
X = np.stack([feats.get(b, np.zeros(len(ro_ids), np.float32)) for b in C])
assert X.shape[1] == len(ro_ids) and X.max() <= 255
bits = np.packbits(X > 0, axis=1, bitorder='little')                  # 판마다 1,171비트: 어떤 출력 뉴런이 발화했나
cnt = X[X > 0].astype(np.uint8)                                        # 발화한 뉴런들의 발화 수, 판 순서대로 이어 붙임

dev = not (have.all() and os.path.exists('ttt/readout.json'))
if not dev:
    r = json.load(open('ttt/readout.json')); mu, sd, w = (np.array(r[k], float) for k in ('mu', 'sd', 'w')); bias = float(r['b'])
else:                                                                  # 임시: 저장된 판만으로 ttt_train과 같은 방식의 판독기
    from ttt_train import fit
    m = fit(np.log1p(X[have].astype(float)), np.array([value(b, 'H') for b in np.array(C)[have]]))
    mu, sd, w, bias = m['mu'], m['sd'], m['w'], m['b']
assert len(mu) == len(sd) == len(w) == len(ro_ids)

data = dict(dev=bool(dev), nHave=int(have.sum()), boards=''.join(C), have=b64(np.packbits(have, bitorder='little')),
            bits=b64(bits), cnt=b64(cnt), nRO=len(ro_ids),
            mu=b64(mu.astype(np.float64)), sd=b64(sd.astype(np.float64)), w=b64(w.astype(np.float64)), b=bias,
            bg=b64(to_i16(bg_ids)), sens=b64(to_i16(sens_ids)), sensCell=b64(L['cell_of'].astype(np.uint8)), ro=b64(to_i16(ro_ids)))
src = open('../viz/ttt.src.html', encoding='utf-8').read()
src = src.replace('__LOGO__', 'data:image/png;base64,' + base64.b64encode(open('../viz/logo_w.png', 'rb').read()).decode())
open('../viz/ttt.html', 'w', encoding='utf-8').write(src.replace('/*DATA*/null', json.dumps(data, separators=(',', ':'))))
print(f'viz/ttt.html  {os.path.getsize("../viz/ttt.html")/1e6:.2f} MB  boards with brain data {have.sum()}/{len(C)}  dev={dev}')
