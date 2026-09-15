"""뇌 발화 수 → 판독기(릿지 회귀) 학습 → 초파리 수 표 + 평가.
초파리는 둘 수 있는 칸마다 '그 칸에 둔 뒤의 판'을 뇌에 넣은 발화 수를 보고, 판독기 점수가 가장 높은 칸을 고른다.
뇌 모델은 고정이고 학습되는 건 판독기(출력 뉴런 발화 수에 곱할 가중치)뿐이다.
산출: ttt/readout.json(태블릿이 쓰는 가중치), ttt/fly_moves.json(대조용 수 표), ttt/report.json(평가)
사용: .venv/bin/python ttt_train.py            (ttt/features_seed0.npz, seed1.npz 필요)
      .venv/bin/python ttt_train.py selftest   (가짜 특징으로 채점 로직 확인)"""
import sys, json, numpy as np
from ttt_game import fly_states, candidates, moves, play, value, winner, OTHER

STATES, CANDS = fly_states(), candidates()
IDX = {b: i for i, b in enumerate(CANDS)}
Y = np.array([value(b, 'H') for b in CANDS], float)             # 초파리가 둔 직후 판의 결과(사람 차례, 양쪽 최선)
CHILD = {s: [play(s, i, 'F') for i in moves(s)] for s in STATES}
CV = {s: [value(c, 'H') for c in CHILD[s]] for s in STATES}
BEST = {s: max(CV[s]) for s in STATES}
MATTERS = [s for s in STATES if len(set(CV[s])) > 1]              # 어느 칸에 두느냐로 결과가 달라지는 판
AVOIDABLE = [s for s in STATES if BEST[s] >= 0]                   # 지는 걸 피할 수 있는 판
SFOLD = dict(zip(STATES, np.random.default_rng(0).permutation(len(STATES)) % 5))
LAMBDAS = [1e-1, 1, 10, 100, 1e3, 1e4, 1e5]
mean = lambda xs: round(float(np.mean(xs)), 4)

def ridge(X, y, lam):
    mu, sd = X.mean(0), X.std(0)
    keep = sd > 1e-3                                              # 학습 판에서 거의 안 변하는 뉴런은 뺀다
    Z = (X[:, keep] - mu[keep]) / sd[keep]
    w = np.zeros(X.shape[1])
    w[keep] = np.linalg.solve(Z.T @ Z + lam * np.eye(Z.shape[1]), Z.T @ (y - y.mean()))
    return dict(mu=mu, sd=np.where(keep, sd, 1.0), w=w, b=float(y.mean()), lam=lam)

def predict(m, X): return ((X - m['mu']) / m['sd']) @ m['w'] + m['b']

def fit(X, y):
    """λ는 넘겨받은 학습 판 안에서만 5겹 교차검증으로 고른다."""
    inner = np.random.default_rng(1).permutation(len(y)) % 5
    mse = lambda lam: sum(((predict(ridge(X[inner != k], y[inner != k], lam), X[inner == k]) - y[inner == k]) ** 2).sum() for k in range(5))
    return ridge(X, y, min(LAMBDAS, key=mse))

def choose(score, s): return max(moves(s), key=lambda i: (score[play(s, i, 'F')], -i))

def heldout(X, Xtest=None):
    """초파리 차례 판 단위 5겹: 시험 판의 후보 판은 전부 학습에서 빼고, 한 판독기가 한꺼번에 점수를 매긴다."""
    Xtest = X if Xtest is None else Xtest
    choice, lams = {}, []
    for k in range(5):
        ts = [s for s in STATES if SFOLD[s] == k]
        tb = sorted({c for s in ts for c in CHILD[s]})
        tr = np.ones(len(CANDS), bool); tr[[IDX[b] for b in tb]] = False
        m = fit(X[tr], Y[tr]); lams.append(m['lam'])
        sc = dict(zip(tb, predict(m, Xtest[[IDX[b] for b in tb]])))
        choice.update({s: choose(sc, s) for s in ts})
    return choice, lams

def insample(X):
    m = fit(X, Y); sc = dict(zip(CANDS, predict(m, X)))
    return {s: choose(sc, s) for s in STATES}, m, sc

def grade(choice):
    v = {s: value(play(s, choice[s], 'F'), 'H') for s in STATES}
    return {'best_move_all_positions': mean([v[s] == BEST[s] for s in STATES]),
            'best_move_where_choice_matters': mean([v[s] == BEST[s] for s in MATTERS]),
            'lost_when_loss_was_avoidable': mean([v[s] == -1 for s in AVOIDABLE])}

def random_grade():
    frac = lambda s, f: sum(map(f, CV[s])) / len(CV[s])
    return {'best_move_all_positions': mean([frac(s, lambda v: v == BEST[s]) for s in STATES]),
            'best_move_where_choice_matters': mean([frac(s, lambda v: v == BEST[s]) for s in MATTERS]),
            'lost_when_loss_was_avoidable': mean([frac(s, lambda v: v == -1) for s in AVOIDABLE])}

def game(starter, fly, human, rng):
    b, p = '.' * 9, starter
    while winner(b) is None and '.' in b:
        b = play(b, fly(b, rng) if p == 'F' else human(b, rng), p); p = OTHER[p]
    return winner(b) or 'D'

def random_pick(b, rng): return int(rng.choice(moves(b)))
def perfect_for(p):
    def pick(b, rng):
        ms = moves(b); vals = [value(play(b, i, p), OTHER[p]) for i in ms]
        best = max(vals) if p == 'F' else min(vals)
        return int(rng.choice([i for i, v in zip(ms, vals) if v == best]))
    return pick

MATCHUPS = [(h, st) for h in ('random_human', 'perfect_human') for st in 'HF']
def matches(fly, n=1000):
    out = {}
    for hname, starter in MATCHUPS:
        human = random_pick if hname == 'random_human' else perfect_for('H')
        rng = np.random.default_rng(7)
        r = [game(starter, fly, human, rng) for _ in range(n)]
        out[f'vs_{hname}_{"human_first" if starter == "H" else "fly_first"}'] = {'fly_win': r.count('F'), 'draw': r.count('D'), 'fly_loss': r.count('H')}
    return out
table_player = lambda choice: (lambda b, rng: choice[b])

def assist_move(s):
    """뇌 밖 보조 규칙(태블릿과 같음): 바로 이기는 칸, 없으면 사람이 바로 이길 칸."""
    return next((i for p in 'FH' for i in moves(s) if winner(play(s, i, p)) == p), None)
def with_assists(choice): return {s: choice[s] if assist_move(s) is None else assist_move(s) for s in STATES}
def assisted_pick(pick): return lambda b, rng: pick(b, rng) if assist_move(b) is None else assist_move(b)

def load(seed):
    z = np.load(f'ttt/features_seed{seed}.npz'); d = dict(zip(z['boards'], z['X']))
    return np.log1p(np.stack([d[b] for b in CANDS]).astype(float))

def onehot(bs): return np.array([[c == 'H' for c in b] + [c == 'F' for c in b] for b in bs], float)
def random_network(seed, B, d=1171):
    """판 원-핫 B를 무작위 ReLU 층으로 d차원까지 늘린 대조군"""
    rng = np.random.default_rng(seed)
    return np.maximum(0, B @ rng.normal(size=(B.shape[1], d)) + rng.normal(size=d))

def spread(xs): xs = sorted(xs); return {'min': xs[0], 'median': xs[len(xs) // 2], 'max': xs[-1], 'n': len(xs)}

if __name__ == '__main__':
    base = random_grade()
    if sys.argv[1:] == ['selftest']:
        leak = np.hstack([onehot(CANDS), Y[:, None] + np.random.default_rng(2).normal(0, .05, (len(Y), 1))])
        g = grade(heldout(leak)[0]); assert g['best_move_all_positions'] > 0.95, g
        noise = np.random.default_rng(3).normal(size=(len(Y), 1171))
        g2 = grade(heldout(noise)[0]); assert g2['best_move_all_positions'] < base['best_move_all_positions'] + 0.05, (g2, base)
        print('selftest ok | random mover', base, '| leaked answer, held-out', g, '| 1171-dim noise, held-out', g2); sys.exit()

    X0, X1 = load(0), load(1)
    rep = {'_note': ('heldout = 시험하는 초파리 차례 판의 후보 판을 학습에서 뺀 판독기로 채점. '
                     'exhibit = 모든 판으로 학습한 뒤 같은 판에서 채점(태블릿이 실제로 쓰는 표). '
                     'shuffled_null = 판과 발화 수의 짝을 무작위로 섞어 판 정보를 없앤 대조군, 같은 절차로 학습.'),
           'n_fly_positions': len(STATES), 'n_positions_where_choice_matters': len(MATTERS), 'n_boards_simulated': len(CANDS),
           'random_mover': base, 'heldout': {}, 'exhibit': {}}
    H = rep['heldout']
    for name, X in [('fly_brain', X0), ('board_onehot_linear', onehot(CANDS))]:
        ch, lams = heldout(X); H[name] = grade(ch) | {'lambdas': lams}
    ch, _ = heldout(X0, X1); H['fly_brain_tested_on_new_noise'] = grade(ch)
    H['random_network_control_5_draws'] = {k: spread([g[k] for g in [grade(heldout(random_network(40 + r, onehot(CANDS)))[0]) for r in range(5)]]) for k in base}
    perm = np.random.default_rng(9).permutation(len(CANDS))
    H['shuffled_null'] = grade(heldout(X0[perm])[0])

    E = rep['exhibit']
    fly_choice, fly_model, S0 = insample(X0)
    E['fly_brain'] = grade(fly_choice) | {'lambda': fly_model['lam']}
    re_choice = {s: choose(dict(zip(CANDS, predict(fly_model, X1))), s) for s in STATES}
    E['fly_brain_table_if_resimulated_with_new_noise'] = grade(re_choice) | {
        'same_move_where_choice_matters': mean([re_choice[s] == fly_choice[s] for s in MATTERS]),
        'same_move_by_chance_where_choice_matters': mean([1 / len(moves(s)) for s in MATTERS])}
    E['fly_brain_with_2_assists'] = grade(with_assists(fly_choice))
    E['board_onehot_linear'] = grade(insample(onehot(CANDS))[0])
    E['random_network_control'] = grade(insample(random_network(40, onehot(CANDS)))[0])
    null_games, null_grades = [], []
    for r in range(20):
        ch = insample(X0[np.random.default_rng(100 + r).permutation(len(CANDS))])[0]
        null_grades.append((grade(ch), grade(with_assists(ch)))); null_games.append((matches(table_player(ch)), matches(table_player(with_assists(ch)))))
    E['shuffled_null_20'] = {k: spread([g[0][k] for g in null_grades]) for k in base}
    E['shuffled_null_20_with_2_assists'] = {k: spread([g[1][k] for g in null_grades]) for k in base}

    fly_games = matches(table_player(fly_choice))
    notlose = lambda gs, m: spread([g[m]['fly_win'] + g[m]['draw'] for g in gs])
    rep['games_1000_each'] = {'fly_brain_exhibit_table': fly_games,
                              'fly_brain_with_2_assists_(tablet)': matches(table_player(with_assists(fly_choice))),
                              'random_mover': matches(random_pick), 'random_mover_with_2_assists': matches(assisted_pick(random_pick)),
                              'perfect_player': matches(perfect_for('F')),
                              'shuffled_null_20_not_losing': {m: notlose([g[0] for g in null_games], m) for m in fly_games},
                              'shuffled_null_20_with_2_assists_not_losing': {m: notlose([g[1] for g in null_games], m) for m in fly_games}}

    json.dump({'mu': fly_model['mu'].tolist(), 'sd': fly_model['sd'].tolist(), 'w': fly_model['w'].tolist(), 'b': fly_model['b'], 'lambda': fly_model['lam']},
              open('ttt/readout.json', 'w'))
    json.dump({s: {'move': fly_choice[s], 'scores': {str(i): round(float(S0[play(s, i, 'F')]), 4) for i in moves(s)}} for s in STATES},
              open('ttt/fly_moves.json', 'w'), separators=(',', ':'))
    json.dump(rep, open('ttt/report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
