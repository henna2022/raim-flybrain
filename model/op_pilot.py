"""옥타폰 관문 G1: 뇌 신호가 형제 후보 판(같은 판에서 초파리가 다르게 둔 결과)을 잡음보다 크게 구분하나.
r_op = 형제 후보 판끼리 거리 중앙값 / 같은 판 seed 0·1 거리 중앙값 (log1p 발화 수). 통과: r_op >= 0.8 × r_ttt(1.128)."""
import json, time, numpy as np
from multiprocessing import Pool
from op_game import fly_states, moves, play

def init():
    import ttt_sim; ttt_sim.build('cython', n_groups=32)

def work(args):
    import ttt_sim
    b, seed = args
    return b, seed, ttt_sim.features(b, seed)

if __name__ == '__main__':
    rng = np.random.default_rng(0)
    states = [s for s in fly_states() if len(moves(s, 'F')) >= 2]
    groups, boards = [], []
    for i in rng.permutation(len(states)):
        kids = sorted({play(states[i], m, 'F') for m in moves(states[i], 'F')})
        if len(kids) < 2: continue
        groups.append(kids); boards += [k for k in kids if k not in boards]
        if len(boards) >= 350: break
    t0 = time.time()
    with Pool(5, initializer=init) as pool:
        res = pool.map(work, [(b, s) for s in (0, 1) for b in boards], chunksize=4)
    F = {(b, s): np.log1p(f.astype(float)) for b, s, f in res}
    sib = [np.linalg.norm(F[(a, 0)] - F[(c, 0)]) for g in groups for i, a in enumerate(g) for c in g[i + 1:]]
    noise = [np.linalg.norm(F[(b, 0)] - F[(b, 1)]) for b in boards]
    raw0 = np.array([np.expm1(F[(b, 0)]) for b in boards])
    out = {'boards': len(boards), 'sibling_pairs': len(sib), 'minutes': round((time.time() - t0) / 60, 1),
           'r_op': round(float(np.median(sib) / np.median(noise)), 3), 'r_ttt': 1.128, 'threshold': round(0.8 * 1.128, 3),
           'spikes_per_board': round(float(raw0.sum(1).mean())), 'active_readout_per_board': round(float((raw0 > 0).sum(1).mean()))}
    out['pass'] = out['r_op'] >= out['threshold']
    np.savez('op/pilot.npz', boards=np.array(boards), X0=np.array([np.expm1(F[(b, 0)]) for b in boards], np.float32), X1=np.array([np.expm1(F[(b, 1)]) for b in boards], np.float32))
    json.dump(out, open('op/pilot.json', 'w'), indent=1); print(json.dumps(out, indent=1))
