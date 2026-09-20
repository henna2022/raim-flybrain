// 체스 규칙. 판은 64글자, 0번이 a8(왼쪽 위), 63번이 h1(오른쪽 아래). 대문자가 흰 편.
// 초파리가 둘 수 있는 수를 모두 만들어 하나씩 신경망에 넣어 보려면 합법수 판정이 정확해야 한다.
// 정확성은 perft(정해진 깊이까지 수를 모두 세는 표준 검사)로 확인한다.

export const START = 'rnbqkbnrpppppppp' + '.'.repeat(32) + 'PPPPPPPPRNBQKBNR';
export const newGame = () => ({ b: START, w: true, cas: 'KQkq', ep: -1, half: 0 });

const isW = c => c !== '.' && c === c.toUpperCase();
const mine = (c, w) => c !== '.' && isW(c) === w;
const N = -8, S = 8, E = 1, W = -1;
const KNIGHT = [-17, -15, -10, -6, 6, 10, 15, 17];
const KING = [-9, -8, -7, -1, 1, 7, 8, 9];
const file = i => i & 7, rank = i => i >> 3;
const ok = i => i >= 0 && i < 64;
// 가장자리를 넘어가는 이동을 거른다 (파일 차이가 2칸을 넘으면 반대쪽으로 넘어간 것)
const near = (a, b, max) => ok(b) && Math.abs(file(a) - file(b)) <= max;

function slide(b, i, dirs, w, out) {
  for (const d of dirs) {
    let p = i;
    for (;;) {
      const q = p + d;
      if (!near(p, q, 1)) break;
      if (b[q] === '.') { out.push([i, q]); p = q; continue; }
      if (!mine(b[q], w)) out.push([i, q]);
      break;
    }
  }
}

/** 왕이 잡히는지는 보지 않은 수 목록 */
function pseudo(s) {
  const { b, w, ep } = s, out = [];
  const up = w ? N : S, home = w ? 6 : 1, last = w ? 0 : 7;
  for (let i = 0; i < 64; i++) {
    const c = b[i];
    if (!mine(c, w)) continue;
    const t = c.toUpperCase();
    if (t === 'P') {
      const one = i + up;
      if (ok(one) && b[one] === '.') {
        pushPawn(out, i, one, rank(one) === last);
        const two = one + up;
        if (rank(i) === home && b[two] === '.') out.push([i, two]);
      }
      for (const d of [W, E]) {
        const q = i + up + d;
        if (!near(i, q, 1)) continue;
        if (b[q] !== '.' && !mine(b[q], w)) pushPawn(out, i, q, rank(q) === last);
        else if (q === ep) out.push([i, q]);
      }
    } else if (t === 'N') {
      for (const d of KNIGHT) { const q = i + d; if (near(i, q, 2) && !mine(b[q], w)) out.push([i, q]); }
    } else if (t === 'K') {
      for (const d of KING) { const q = i + d; if (near(i, q, 1) && !mine(b[q], w)) out.push([i, q]); }
    } else {
      const dirs = t === 'B' ? [N + W, N + E, S + W, S + E]
                 : t === 'R' ? [N, S, E, W]
                 : [N, S, E, W, N + W, N + E, S + W, S + E];
      slide(b, i, dirs, w, out);
    }
  }
  castles(s, out);
  return out;
}

function pushPawn(out, from, to, promo) {
  if (promo) for (const p of 'QRBN') out.push([from, to, p]);
  else out.push([from, to]);
}

function castles(s, out) {
  const { b, w, cas } = s, k = w ? 60 : 4;
  if (b[k] !== (w ? 'K' : 'k') || attacked(s, k, !w)) return;
  const rights = w ? ['K', 'Q'] : ['k', 'q'];
  if (cas.includes(rights[0]) && b[k + 1] === '.' && b[k + 2] === '.' &&
      !attacked(s, k + 1, !w) && !attacked(s, k + 2, !w)) out.push([k, k + 2]);
  if (cas.includes(rights[1]) && b[k - 1] === '.' && b[k - 2] === '.' && b[k - 3] === '.' &&
      !attacked(s, k - 1, !w) && !attacked(s, k - 2, !w)) out.push([k, k - 2]);
}

/** 칸 i 를 by 쪽(true=흰)이 공격하고 있나 */
export function attacked(s, i, by) {
  const b = s.b;
  for (const d of KNIGHT) { const q = i + d; if (near(i, q, 2) && b[q] === (by ? 'N' : 'n')) return true; }
  for (const d of KING) { const q = i + d; if (near(i, q, 1) && b[q] === (by ? 'K' : 'k')) return true; }
  const up = by ? S : N;                                  // by 편 폰은 i 에서 볼 때 반대쪽에 있다
  for (const d of [W, E]) { const q = i + up + d; if (near(i, q, 1) && b[q] === (by ? 'P' : 'p')) return true; }
  const rook = by ? 'RQ' : 'rq', bish = by ? 'BQ' : 'bq';
  for (const [dirs, set] of [[[N, S, E, W], rook], [[N + W, N + E, S + W, S + E], bish]]) {
    for (const d of dirs) {
      let p = i;
      for (;;) {
        const q = p + d;
        if (!near(p, q, 1)) break;
        if (b[q] !== '.') { if (set.includes(b[q])) return true; break; }
        p = q;
      }
    }
  }
  return false;
}

export const kingAt = (b, w) => b.indexOf(w ? 'K' : 'k');
export const inCheck = s => attacked(s, kingAt(s.b, s.w), !s.w);

export function make(s, m) {
  const [from, to, promo] = m;
  const a = s.b.split(''), c = a[from], t = c.toUpperCase(), w = s.w;
  const cap = a[to] !== '.' || (t === 'P' && to === s.ep);
  a[to] = promo ? (w ? promo : promo.toLowerCase()) : c;
  a[from] = '.';
  if (t === 'P' && to === s.ep) a[to + (w ? S : N)] = '.';             // 앙파상으로 잡힌 폰
  if (t === 'K' && Math.abs(file(from) - file(to)) === 2) {            // 캐슬링이면 룩도 옮긴다
    const rf = to > from ? from + 3 : from - 4, rt = to > from ? to - 1 : to + 1;
    a[rt] = a[rf]; a[rf] = '.';
  }
  let cas = s.cas;
  const drop = ch => { cas = cas.replace(ch, ''); };
  if (t === 'K') { drop(w ? 'K' : 'k'); drop(w ? 'Q' : 'q'); }
  for (const [sq, ch] of [[63, 'K'], [56, 'Q'], [7, 'k'], [0, 'q']]) if (from === sq || to === sq) drop(ch);
  return { b: a.join(''), w: !w, cas: cas || '-',
           ep: t === 'P' && Math.abs(from - to) === 16 ? (from + to) / 2 : -1,
           half: (cap || t === 'P') ? 0 : s.half + 1 };
}

/** 왕이 잡히지 않는 수만 */
export function moves(s) {
  return pseudo(s).filter(m => {
    const n = make(s, m);
    return !attacked(n, kingAt(n.b, s.w), !s.w);
  });
}

/** 'checkmate' | 'stalemate' | 'draw50' | null */
export function result(s) {
  if (moves(s).length === 0) return inCheck(s) ? 'checkmate' : 'stalemate';
  return s.half >= 100 ? 'draw50' : null;
}

export const sqName = i => 'abcdefgh'[file(i)] + (8 - rank(i));

export function perft(s, d) {
  if (d === 0) return 1;
  let n = 0;
  for (const m of moves(s)) n += perft(make(s, m), d - 1);
  return n;
}
