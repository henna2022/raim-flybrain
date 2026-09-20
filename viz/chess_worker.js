// 초파리가 수를 고르는 계산을 화면과 따로 돌린다. 수 하나에 수십 밀리초가 걸려서
// 같은 자리에서 돌리면 화면이 멈추고 뇌 그림도 안 움직인다.
// 화면 쪽에서 쓰는 법:
//   const w = new Worker('/chess_worker.js', { type: 'module' });
//   w.postMessage({ type: 'load' });                       -> { type:'ready' } 또는 { type:'error' }
//   w.postMessage({ type: 'think', board, white, moves }); -> 수마다 { type:'step' }, 끝나면 { type:'done' }
// step 에는 그 수를 놓아 본 판의 승률(p)과 뇌 점들의 활동(act, 0~255)이 담긴다.
import { loadNet, evaluate, encodeBoard } from './flynet.js';
import { make } from './chess_rules.js';

let net = null, idx = null, gen = 0;

async function load() {
  net = await loadNet('/net/', f => postMessage({ type: 'loading', frac: f }));
  idx = new Int32Array(await fetch('/net/npt_idx.bin').then(r => r.arrayBuffer()));
  postMessage({ type: 'ready', meta: net.meta, points: idx.length });
}

/** 뇌 점들의 활동을 0~255로 줄여 보낸다. 최대값으로 나눠 판마다 밝기가 비슷하게 보이게 한다 */
function sample(r) {
  const out = new Uint8Array(idx.length);
  let max = 0;
  for (let i = 0; i < idx.length; i++) { const v = r[idx[i]]; if (v > max) max = v; }
  if (max > 0) for (let i = 0; i < idx.length; i++) out[i] = Math.min(255, Math.round(r[idx[i]] / max * 255));
  return out;
}

/** 둘 수 있는 수를 하나씩 놓아 보고 승률을 잰다. 초파리는 앞을 내다보지 않고 한 수만 본다 */
function think({ board, white, moves, half, cas, ep }) {
  const my = ++gen;
  let best = null;
  for (let i = 0; i < moves.length; i++) {
    if (my !== gen) return;                                     // 새 요청이 오면 하던 계산을 버린다
    const after = make({ b: board, w: white, cas: cas ?? '-', ep: ep ?? -1, half: half ?? 0 }, moves[i]);
    // 수를 둔 뒤 판은 상대 차례다. 상대가 이길 가능성을 재서 뒤집으면 내가 이길 가능성이 된다
    const { p, r } = evaluate(net, Int32Array.from(encodeBoard(after.b, after.w ? 'w' : 'b')));
    const mineWins = 1 - p;
    if (!best || mineWins > best.p) best = { i, move: moves[i], p: mineWins };
    postMessage({ type: 'step', i, n: moves.length, move: moves[i], p: mineWins,
                  best: best.i, act: sample(r) });
  }
  postMessage({ type: 'done', best });
}

onmessage = async (e) => {
  const m = e.data;
  try {
    if (m.type === 'load') return void await load();
    if (m.type === 'think') {
      if (!net) throw new Error('신경망이 아직 안 올라왔어요');
      return void think(m);
    }
    if (m.type === 'cancel') return void gen++;
  } catch (err) {
    postMessage({ type: 'error', message: String(err && err.message || err) });
  }
};
