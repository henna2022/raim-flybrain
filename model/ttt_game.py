"""틱택토 규칙, 판 열거, 미니맥스. 판은 9글자: H=사람, F=초파리, .=빈칸."""
from functools import lru_cache
LINES = [(0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),(0,4,8),(2,4,6)]
OTHER = {'H': 'F', 'F': 'H'}

def winner(b):
    for i, j, k in LINES:
        if b[i] != '.' and b[i] == b[j] == b[k]:
            return b[i]
    return None

def over(b): return winner(b) is not None or '.' not in b
def moves(b): return [i for i, c in enumerate(b) if c == '.']
def play(b, i, p): return b[:i] + p + b[i+1:]

@lru_cache(None)
def value(b, to_move):
    """초파리 관점 결과(양쪽 최선): +1 초파리 승, 0 무, -1 사람 승."""
    w = winner(b)
    if w: return 1 if w == 'F' else -1
    if '.' not in b: return 0
    vals = [value(play(b, i, to_move), OTHER[to_move]) for i in moves(b)]
    return max(vals) if to_move == 'F' else min(vals)

def fly_states():
    """초파리 차례인 도달 가능한 모든 판. 사람 먼저·초파리 먼저 둘 다."""
    seen, out = set(), set()
    def walk(b, p):
        if (b, p) in seen: return
        seen.add((b, p))
        if over(b): return
        if p == 'F': out.add(b)
        for i in moves(b): walk(play(b, i, p), OTHER[p])
    walk('.' * 9, 'H'); walk('.' * 9, 'F')
    return sorted(out)

def candidates():
    """초파리가 한 수 둔 직후의 판 전부. 이것만 뇌에 넣어 본다."""
    return sorted({play(s, i, 'F') for s in fly_states() for i in moves(s)})

if __name__ == '__main__':
    S, C = fly_states(), candidates()
    assert value('.' * 9, 'H') == 0 and value('.' * 9, 'F') == 0   # 틱택토는 최선이면 무승부
    assert value('HH.FF....', 'F') == 1 and value('FF.HH....', 'H') == -1
    print('fly-to-move states', len(S), '| boards to simulate', len(C))
