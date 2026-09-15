"""옥타폰 판독기 학습·평가 (ttt_train.py와 같은 방식). 뇌는 고정, 학습하는 건 뇌 밖 릿지 판독기뿐.
산출: op/readout.json(태블릿용 가중치), op/fly_moves.json(수 표), op/report.json(평가, 관문 G2 판정 포함)
사용: python op_train.py            (op/features_seed0.npz, seed1.npz 필요)
      python op_train.py selftest   (가짜 특징으로 채점 로직 확인, 시뮬 데이터 없이 돈다)"""
import sys, json, numpy as np
from op_game import fly_states, candidates, moves, play, value, winner, START, OTHER
from ttt_train import predict, fit, spread, mean, onehot, random_network   # 게임과 무관한 부분만 가져온다

STATES, CANDS = fly_states(), candidates()
IDX = {b: i for i, b in enumerate(CANDS)}
Y = np.array([value(b, 'H') for b in CANDS], float)      # 초파리가 둔 직후 판의 결과(양쪽 최선): +1 이김, -1 짐
CHILD = {s: [play(s, m, 'F') for m in moves(s, 'F')] for s in STATES}
CV = {s: [value(c, 'H') for c in CHILD[s]] for s in STATES}
BEST = {s: max(CV[s]) for s in STATES}
MATTERS = [s for s in STATES if len(set(CV[s])) > 1]      # 어느 수를 두느냐로 승패가 갈리는 판
WINNABLE = [s for s in STATES if BEST[s] == 1]
SFOLD = dict(zip(STATES, np.random.default_rng(0).permutation(len(STATES)) % 5))

def choose(score, s):
    ms = moves(s, 'F')
    return max(ms, key=lambda m: (score[play(s, m, 'F')], -ms.index(m)))

def heldout(X, Xtest=None):
    """초파리 차례 판 단위 5겹: 시험 판의 후보 판은 전부 학습에서 빼고, 한 판독기가 점수를 매긴다."""
    Xtest = X if Xtest is None else Xtest
    choice = {}
    for k in range(5):
        ts = [s for s in STATES if SFOLD[s] == k]
        tb = sorted({c for s in ts for c in CHILD[s]})
        tr = np.ones(len(CANDS), bool); tr[[IDX[b] for b in tb]] = False
        m = fit(X[tr], Y[tr])
        sc = dict(zip(tb, predict(m, Xtest[[IDX[b] for b in tb]])))
        choice.update({s: choose(sc, s) for s in ts})
    return choice

def insample(X):
    m = fit(X, Y); sc = dict(zip(CANDS, predict(m, X)))
    return {s: choose(sc, s) for s in STATES}, m, sc

def grade(choice):
    v = {s: value(play(s, choice[s], 'F'), 'H') for s in STATES}
    return {'best_move_all_positions': mean([v[s] == BEST[s] for s in STATES]),
            'best_move_where_choice_matters': mean([v[s] == BEST[s] for s in MATTERS]),
            'threw_away_a_winnable_position': mean([v[s] == -1 for s in WINNABLE])}

def random_grade():
    frac = lambda s, f: sum(map(f, CV[s])) / len(CV[s])
    return {'best_move_all_positions': mean([frac(s, lambda v: v == BEST[s]) for s in STATES]),
            'best_move_where_choice_matters': mean([frac(s, lambda v: v == BEST[s]) for s in MATTERS]),
            'threw_away_a_winnable_position': mean([frac(s, lambda v: v == -1) for s in WINNABLE])}

def game(starter, fly, human, rng):
    b, p = START, starter
    while True:
        w = winner(b, p)
        if w: return w
        b = play(b, fly(b, rng) if p == 'F' else human(b, rng), p); p = OTHER[p]

def random_human(b, rng): ms = moves(b, 'H'); return ms[rng.integers(len(ms))]
def perfect_human(b, rng):
    ms = moves(b, 'H'); vals = [value(play(b, m, 'H'), 'F') for m in ms]
    best = [m for m, v in zip(ms, vals) if v == min(vals)]; return best[rng.integers(len(best))]
def random_fly(b, rng): ms = moves(b, 'F'); return ms[rng.integers(len(ms))]
table_player = lambda choice: (lambda b, rng: choice[b])

def matches(fly, n=1000):
    out = {}
    for hname, human in [('random_human', random_human), ('perfect_human', perfect_human)]:
        for starter in 'HF':
            rng = np.random.default_rng(7)
            r = [game(starter, fly, human, rng) for _ in range(n)]
            out[f'vs_{hname}_{"human_first" if starter == "H" else "fly_first"}'] = {'fly_win': r.count('F'), 'fly_loss': r.count('H')}
    return out

def load(seed):
    z = np.load(f'op/features_seed{seed}.npz'); d = dict(zip(z['boards'], z['X']))
    missing = [b for b in CANDS if b not in d]
    assert not missing, f'seed {seed}: 시뮬 안 된 판 {len(missing)}개. ttt_run.py {seed} N --game=op 를 끝까지 돌리세요'
    return np.log1p(np.stack([d[b] for b in CANDS]).astype(float))

if __name__ == '__main__':
    base = random_grade(); K = 'best_move_where_choice_matters'
    if sys.argv[1:] == ['selftest']:
        leak = np.hstack([onehot(CANDS), Y[:, None] + np.random.default_rng(2).normal(0, .05, (len(Y), 1))])
        g = grade(heldout(leak)); assert g['best_move_all_positions'] > 0.95, g
        g2 = grade(heldout(np.random.default_rng(3).normal(size=(len(Y), 1171))))
        assert g2['best_move_all_positions'] < base['best_move_all_positions'] + 0.05, (g2, base)
        fly_first_perfect = matches(lambda b, rng: max(moves(b, 'F'), key=lambda m: value(play(b, m, 'F'), 'H')), n=50)
        assert fly_first_perfect['vs_perfect_human_fly_first']['fly_win'] == 50, fly_first_perfect   # 옥타폰은 먼저 두는 쪽 필승
        print('selftest ok | random mover', base, '| leaked answer', g, '| noise', g2); sys.exit()

    X0, X1 = load(0), load(1)
    H = {}
    H['fly_brain'] = grade(heldout(X0))
    H['fly_brain_tested_on_new_noise'] = grade(heldout(X0, X1))
    H['board_onehot_linear'] = grade(heldout(onehot(CANDS)))
    H['random_network_control_5_draws'] = {k: spread([g[k] for g in [grade(heldout(random_network(40 + r, onehot(CANDS)))) for r in range(5)]]) for k in base}
    nulls = [grade(heldout(X0[np.random.default_rng(200 + r).permutation(len(CANDS))])) for r in range(20)]
    H['shuffled_null_20'] = {k: spread([g[k] for g in nulls]) for k in base}
    gate = {'G2_pass_1_above_shuffled_max': H['fly_brain'][K] > max(g[K] for g in nulls),
            'G2_pass_2_new_noise_drop_le_0.05': H['fly_brain'][K] - H['fly_brain_tested_on_new_noise'][K] <= 0.05}
    gate['G2_pass'] = all(gate.values())

    E = {}
    fly_choice, fly_model, S0 = insample(X0)
    E['fly_brain'] = grade(fly_choice) | {'lambda': fly_model['lam']}
    null_ch = [insample(X0[np.random.default_rng(100 + r).permutation(len(CANDS))])[0] for r in range(20)]
    E['shuffled_null_20'] = {k: spread([grade(c)[k] for c in null_ch]) for k in base}
    fly_games = matches(table_player(fly_choice))
    games = {'fly_brain_exhibit_table': fly_games, 'random_fly': matches(random_fly),
             'shuffled_null_20_fly_wins': {m: spread([g[m]['fly_win'] for g in [matches(table_player(c)) for c in null_ch]]) for m in fly_games}}

    rep = {'_note': ('heldout = 시험하는 초파리 차례 판의 후보 판을 학습에서 뺀 판독기로 채점. exhibit = 모든 판으로 학습한 태블릿용 표. '
                     'shuffled = 판과 발화 수의 짝을 섞어 판 정보를 없앤 대조군. 옥타폰은 비김이 없고 먼저 두는 쪽이 필승.'),
           'n_fly_positions': len(STATES), 'n_positions_where_choice_matters': len(MATTERS), 'n_boards_simulated': len(CANDS),
           'random_mover': base, 'heldout': H, 'gate': gate, 'exhibit': E, 'games_1000_each': games}
    json.dump({'mu': fly_model['mu'].tolist(), 'sd': fly_model['sd'].tolist(), 'w': fly_model['w'].tolist(), 'b': fly_model['b'], 'lambda': fly_model['lam']}, open('op/readout.json', 'w'))
    json.dump({s: {'move': list(fly_choice[s]), 'scores': {f'{m[0]}-{m[1]}': round(float(S0[play(s, m, 'F')]), 4) for m in moves(s, 'F')}} for s in STATES},
              open('op/fly_moves.json', 'w'), separators=(',', ':'))
    json.dump(rep, open('op/report.json', 'w'), indent=1, ensure_ascii=False)
    print(json.dumps({'heldout': H, 'gate': gate, 'exhibit': E}, indent=1, ensure_ascii=False))
