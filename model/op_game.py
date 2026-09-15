"""옥타폰(4×4 폰 게임) 규칙과 판 열거. 판은 16글자, 초파리 기준 방향으로 고정:
초파리(F) 병정은 맨 윗줄(0~3)에서 아래로(+4), 사람(H) 병정은 맨 아랫줄(12~15)에서 위로(-4) 간다.
앞칸이 비었으면 한 칸 전진, 대각선 앞에 상대가 있으면 잡는다. 상대 끝줄에 닿으면 이기고, 둘 수가 없으면 진다."""
from functools import lru_cache
N = 4
START = 'F' * N + '.' * (N * (N - 2)) + 'H' * N
OTHER = {'F': 'H', 'H': 'F'}

def moves(b, p):
    d, out = (N if p == 'F' else -N), []
    for i, x in enumerate(b):
        if x != p: continue
        c, j = i % N, i + d
        if b[j] == '.': out.append((i, j))
        for dc in (-1, 1):
            if 0 <= c + dc < N and b[j + dc] == OTHER[p]: out.append((i, j + dc))
    return out

def play(b, m, p):
    l = list(b); l[m[0]] = '.'; l[m[1]] = p; return ''.join(l)

def winner(b, to_move):
    if 'F' in b[N * (N - 1):]: return 'F'
    if 'H' in b[:N]: return 'H'
    if not moves(b, to_move): return OTHER[to_move]
    return None

@lru_cache(None)
def value(b, to_move):
    """초파리 관점 결과(양쪽 최선): +1 초파리 승, -1 사람 승. 비김은 없다."""
    w = winner(b, to_move)
    if w: return 1 if w == 'F' else -1
    vals = [value(play(b, m, to_move), OTHER[to_move]) for m in moves(b, to_move)]
    return max(vals) if to_move == 'F' else min(vals)

def fly_states():
    seen, out = set(), set()
    def walk(b, p):
        if (b, p) in seen: return
        seen.add((b, p))
        if winner(b, p): return
        if p == 'F': out.add(b)
        for m in moves(b, p): walk(play(b, m, p), OTHER[p])
    walk(START, 'F'); walk(START, 'H')
    return sorted(out)

def candidates():
    return sorted({play(s, m, 'F') for s in fly_states() for m in moves(s, 'F')})

if __name__ == '__main__':
    S, C = fly_states(), candidates()
    print('fly-to-move positions', len(S), '| boards to simulate', len(C))
    print('first player wins:', value(START, 'F') == 1, value(START, 'H') == -1)
