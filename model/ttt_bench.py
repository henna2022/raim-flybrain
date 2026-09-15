import sys, time, numpy as np, ttt_sim as T
T.build(sys.argv[1])
for b in ['H........', 'H........', '....F....', 'H...F....']:
    t0 = time.time(); f = T.features(b, seed=0); print(sys.argv[1], b, f'{time.time()-t0:.2f}s', int(f.sum()), int((f > 0).sum()))
a1, a2, b1 = T.features('H........', 0), T.features('H........', 1), T.features('....F....', 0)
cos = lambda x, y: float(x @ y / np.linalg.norm(x) / np.linalg.norm(y))
print('same seed identical:', np.array_equal(a1, T.features('H........', 0)), '| seed noise dist', round(float(np.linalg.norm(a1 - a2)), 1), '| board diff dist', round(float(np.linalg.norm(a1 - b1)), 1), '| cos', round(cos(a1, a2), 3), round(cos(a1, b1), 3))
