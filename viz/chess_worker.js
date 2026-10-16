// 초파리가 수를 고르는 계산을 화면과 따로 돌린다. 수 하나에 수십 밀리초가 걸려서
// 같은 자리에서 돌리면 화면이 멈추고 뇌 그림도 안 움직인다.
// 화면 쪽에서 쓰는 법:
//   const w = new Worker('/chess_worker.js', { type: 'module' });
//   w.postMessage({ type: 'load' });                       -> { type:'ready' } 또는 { type:'error' }
//   w.postMessage({ type: 'think', run, board, white, moves, cas, ep, half }); -> 수마다 { type:'step', run }, 끝나면 { type:'done', run }
//   w.postMessage({ type: 'cancel' });                     -> 하던 계산을 다음 수에서 멈춘다(결과를 안 보낸다)
// step 에는 그 수를 놓아 본 판의 승률(p)과 뇌 점들의 활동(act, 0~255)이 담긴다. run 은 받은 그대로 돌려줘서 화면이 옛 판 결과를 버릴 수 있다.
import { loadNet, evaluate, encodeBoard } from './flynet.js';
import { make, moves as legalMoves } from './chess_rules.js';

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

// 학습 데이터(라이체스 FEN)는 앙파상으로 실제 잡을 수 있을 때만 앙파상 칸을 적었다(검증 데이터 44판 모두). 같은 규칙으로 넣는다
const epOf = s => s.ep >= 0 && legalMoves(s).some(m => m[1] === s.ep && s.b[m[0]].toUpperCase() === 'P') ? s.ep : -1;

/** 둘 수 있는 수를 하나씩 놓아 보고 승률을 잰다. 초파리는 앞을 내다보지 않고 한 수만 본다 */
async function think({ run, board, white, moves, half, cas, ep }) {
  const my = ++gen;
  let best = null;
  for (let i = 0; i < moves.length; i++) {
    if (i) await new Promise(ok => setTimeout(ok));             // 수 하나마다 쉬어야 cancel·새 요청 메시지가 들어온다
    if (my !== gen) return;                                     // 새 요청이 오면 하던 계산을 버린다
    const after = make({ b: board, w: white, cas: cas ?? '-', ep: ep ?? -1, half: half ?? 0 }, moves[i]);
    // 수를 둔 뒤 판은 상대 차례다. 상대가 이길 가능성을 재서 뒤집으면 내가 이길 가능성이 된다
    const { p, r } = evaluate(net, Int32Array.from(encodeBoard(after.b, after.w ? 'w' : 'b', after.cas, epOf(after))));
    const mineWins = 1 - p;
    if (!best || mineWins > best.p) best = { i, move: moves[i], p: mineWins };
    postMessage({ type: 'step', run, i, n: moves.length, move: moves[i], p: mineWins,
                  best: best.i, act: sample(r) });
  }
  postMessage({ type: 'done', run, best });
}

onmessage = async (e) => {
  const m = e.data;
  try {
    if (m.type === 'load') return void await load();
    if (m.type === 'think') {
      if (!net) throw new Error('신경망이 아직 안 올라왔어요');
      return void await think(m);
    }
    if (m.type === 'cancel') return void gen++;
  } catch (err) {
    postMessage({ type: 'error', message: String(err && err.message || err) });
  }
};
