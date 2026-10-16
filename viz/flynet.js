// 초파리 연결체 신경망을 브라우저에서 직접 돌린다. 체스는 판이 너무 많아 미리 계산해 둘 수 없다.
// 계산은 dl/chess_export_model.py 가 내보낸 값과 완전히 같다(dl/chess_export_model.py --verify 로 확인).
// r=0에서 시작해 r += 0.5*(-r + relu(W r + u + bias)) 를 T번 돌리고, 읽기 뉴런에 head 를 곱해 시그모이드.
// 화면(DOM)을 건드리지 않으므로 웹 워커 안에서도 그대로 돈다.

const FILES = { vals: Float32Array, col: Int32Array, crow: Int32Array, bias: Float32Array,
                gain: Float32Array, sens: Int32Array, ro: Int32Array, head: Float32Array };

export async function loadNet(base = '/net/', onProgress) {
  const meta = await fetch(base + 'net.json').then(r => r.json());
  const names = Object.keys(FILES);
  const net = { meta };
  for (let i = 0; i < names.length; i++) {
    const k = names[i];
    const buf = await fetch(base + k + '.bin').then(r => {
      if (!r.ok) throw new Error(`${k}.bin 을 못 받았어요 (${r.status})`);
      return r.arrayBuffer();
    });
    net[k] = new FILES[k](buf);
    onProgress?.((i + 1) / names.length);
  }
  if (net.vals.length !== meta.edges) throw new Error('연결 수가 net.json 과 다릅니다');
  net.r = new Float32Array(meta.n);
  net.nx = new Float32Array(meta.n);      // 한 단계는 옛 r 로만 계산해야 한다. 제자리에서 고치면 값이 폭주한다
  net.u = new Float32Array(meta.n);
  return net;
}

// 판 780비트(0/1 Float32Array 또는 켜진 자리 번호 배열) -> {p: 승률, r: 뉴런 활동}
export function evaluate(net, bits) {
  const { n, T, per } = net.meta;
  const { vals, col, crow, bias, gain, sens, ro, head, u, r, nx } = net;
  u.set(bias);
  if (bits.length === net.meta.bits) {                       // 0/1 배열
    for (let j = 0; j < bits.length; j++) {
      if (!bits[j]) continue;
      const v = bits[j] * gain[j];
      for (let k = 0; k < per; k++) u[sens[j * per + k]] += v;
    }
  } else {                                                    // 켜진 자리 번호만
    for (const j of bits) {
      const v = gain[j];
      for (let k = 0; k < per; k++) u[sens[j * per + k]] += v;
    }
  }
  r.fill(0);
  for (let t = 0; t < T; t++) {
    for (let i = 0; i < n; i++) {                       // 먼저 전부 옛 r 로 계산하고
      let s = u[i];
      for (let k = crow[i], e = crow[i + 1]; k < e; k++) s += vals[k] * r[col[k]];
      nx[i] = s > 0 ? s : 0;
    }
    for (let i = 0; i < n; i++) r[i] += 0.5 * (nx[i] - r[i]);   // 그다음 한꺼번에 바꾼다
  }
  let z = head[head.length - 1];
  for (let i = 0; i < ro.length; i++) z += r[ro[i]] * head[i];
  return { p: 1 / (1 + Math.exp(-z)), r };
}

// 자기 차례 쪽 눈으로 본 780비트(dl/chess_data.py encode 와 같은 규칙). board 는 64글자(맨 앞 8글자가 8번째 줄), 대문자가 자기 편.
// 자기 편이 소문자일 때는 위아래를 뒤집고 대소문자를 바꿔 늘 대문자가 둘 차례가 되게 한다(학습 때와 같은 규칙). 캐슬링 글자도 바꾼다.
// cas 는 'KQkq' 꼴(없으면 '-'), ep 는 앙파상 칸 번호(-1 없음). 앙파상은 열만 쓰므로 뒤집어도 그대로다.
const PIECES = 'PNBRQKpnbrqk';
const swap = c => c === c.toUpperCase() ? c.toLowerCase() : c.toUpperCase();
export function encodeBoard(board, mine = 'w', cas = '-', ep = -1) {
  let b = board;
  if (mine === 'b') {
    let f = '';
    for (let row = 7; row >= 0; row--) {
      const s = b.slice(row * 8, row * 8 + 8);
      for (const c of s) f += swap(c);
    }
    b = f;
  }
  const on = [];
  for (let i = 0; i < 64; i++) {
    const c = b[i];
    if (c !== '.') on.push(PIECES.indexOf(c) * 64 + i);
  }
  for (const c of cas) { const k = 'KQkq'.indexOf(mine === 'b' ? swap(c) : c); if (k >= 0) on.push(768 + k); }   // 768~771
  if (ep >= 0) on.push(772 + (ep & 7));                                                                         // 772~779 앙파상 열
  return on;
}
