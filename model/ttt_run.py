"""5,477판 전부를 뇌 모델에 넣어 발화 수를 저장. 끊겨도 이어서 돈다.
사용: .venv/bin/python ttt_run.py SEED [WORKERS] [LIMIT]  → ttt/features_seed{SEED}.npz"""
import sys, os, time, numpy as np
from multiprocessing import Pool
from ttt_game import candidates

def init():
    import ttt_sim; ttt_sim.build('cython')

def work(args):
    import ttt_sim
    b, seed = args
    return b, ttt_sim.features(b, seed)

if __name__ == '__main__':
    seed, workers = int(sys.argv[1]), int(sys.argv[2]) if len(sys.argv) > 2 else 5
    boards = candidates()[: int(sys.argv[3])] if len(sys.argv) > 3 else candidates()
    out = f'ttt/features_seed{seed}{"_test" if len(sys.argv) > 3 else ""}.npz'
    done = {}
    if os.path.exists(out):
        z = np.load(out); done = dict(zip(z['boards'], z['X']))
    todo = [(b, seed) for b in boards if b not in done]
    def save():
        ks = sorted(done); np.savez(out + '.tmp.npz', boards=np.array(ks), X=np.stack([done[k] for k in ks]))
        os.replace(out + '.tmp.npz', out)
    print(f'seed {seed}: {len(done)} done, {len(todo)} to go, {workers} workers', flush=True)
    t0 = time.time()
    with Pool(workers, initializer=init) as pool:
        for n, (b, f) in enumerate(pool.imap_unordered(work, todo, chunksize=4), 1):
            done[b] = f
            if n % 250 == 0 or n == len(todo):
                save(); el = time.time() - t0
                print(f'  {n}/{len(todo)}  {el/60:.1f} min  eta {el/n*(len(todo)-n)/60:.1f} min', flush=True)
    print('saved', out, flush=True)
