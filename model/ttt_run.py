"""게임 판 전부를 뇌 모델에 넣어 발화 수를 저장. 끊겨도 이어서 돈다.
사용: .venv/bin/python ttt_run.py SEED [WORKERS] [LIMIT] [--game=op]
  틱택토 5,477판 → ttt/features_seed{SEED}.npz, 옥타폰 13,854판(--game=op) → op/features_seed{SEED}.npz"""
import sys, os, time, numpy as np
from multiprocessing import Pool
GAME = "op" if "--game=op" in sys.argv else "ttt"
sys.argv = [a for a in sys.argv if not a.startswith("--game")]
if GAME == "op":
    from op_game import candidates
else:
    from ttt_game import candidates
GROUPS = {"ttt": 18, "op": 32}[GAME]

def init(n_groups):
    import ttt_sim; ttt_sim.build('cython', n_groups)

def work(args):
    import ttt_sim
    b, seed = args
    return b, ttt_sim.features(b, seed)

if __name__ == '__main__':
    seed, workers = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 5
    boards = candidates()[: int(sys.argv[3])] if len(sys.argv) > 3 else candidates()
    out = f'{GAME}/features_seed{seed}{"_test" if len(sys.argv) > 3 else ""}.npz'
    done = {}
    if os.path.exists(out):
        z = np.load(out); done = dict(zip(z['boards'], z['X']))
    todo = [(b, seed) for b in boards if b not in done]
    def save():
        ks = sorted(done); np.savez_compressed(out + '.tmp.npz', boards=np.array(ks), X=np.stack([done[k] for k in ks]))
        os.replace(out + '.tmp.npz', out)
    print(f'seed {seed}: {len(done)} done, {len(todo)} to go, {workers} workers', flush=True)
    t0 = time.time()
    with Pool(workers, initializer=init, initargs=(GROUPS,)) as pool:
        for n, (b, f) in enumerate(pool.imap_unordered(work, todo, chunksize=4), 1):
            done[b] = f
            if n % 250 == 0 or n == len(todo):
                save(); el = time.time() - t0
                print(f'  {n}/{len(todo)}  {el/60:.1f} min  eta {el/n*(len(todo)-n)/60:.1f} min', flush=True)
    print('saved', out, flush=True)
