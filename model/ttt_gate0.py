"""체스 계획 관문 G0: 틱택토에서 뇌 신호가 처음 보는 판에도 통하는지.
1) 처음 보는 판 성적(수 선택이 결과를 바꾸는 판)이 판-신호 짝을 섞은 대조군 20회의 최댓값보다 높은가
2) 새 잡음(seed 1)으로 채점해도 0.05 넘게 떨어지지 않는가
3) r_ttt = 형제 후보 판끼리 신호 거리 중앙값 / 같은 판 seed 0·1 거리 중앙값 (옥타폰 파일럿 기준값)"""
import json, numpy as np, ttt_train as T
X0, X1 = T.load(0), T.load(1)
k = 'best_move_where_choice_matters'
fly = T.grade(T.heldout(X0)[0])[k]
fly_new_noise = T.grade(T.heldout(X0, X1)[0])[k]
null = [T.grade(T.heldout(X0[np.random.default_rng(200 + r).permutation(len(T.CANDS))])[0])[k] for r in range(20)]
sib = [np.linalg.norm(X0[T.IDX[a]] - X0[T.IDX[b]]) for s in T.STATES for i, a in enumerate(T.CHILD[s]) for b in T.CHILD[s][i + 1:]]
seed = np.linalg.norm(X0 - X1, axis=1)
out = {'heldout_fly': fly, 'heldout_fly_new_noise': fly_new_noise, 'drop': round(fly - fly_new_noise, 4),
       'heldout_shuffled_20': T.spread(null), 'random_mover': T.random_grade()[k],
       'r_ttt': round(float(np.median(sib) / np.median(seed)), 3),
       'pass_1_above_null_max': fly > max(null), 'pass_2_drop_le_0.05': (fly - fly_new_noise) <= 0.05}
json.dump(out, open('ttt/gate0.json', 'w'), indent=1); print(json.dumps(out, indent=1))
