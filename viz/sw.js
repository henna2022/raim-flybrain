// 화면·앱 코드(html·js·json)는 네트워크 먼저(고치면 바로 반영)이되 3초 안에 답이 없으면 저장본(느린 와이파이에서 멈추지 않게).
// 신경망(/net/ 21 MB)·vendor·글꼴·그림은 저장본 먼저. 이것들을 바꿀 때는 CACHE 판을 꼭 올린다.
// 설치 때 세 체험 화면을 미리 저장해 와이파이가 없어도 돌아가게 한다.
const CACHE = 'raim-flybrain-v29';
const CORE = ['/', '/index.html', '/i18n.js', '/collect.js', '/snack.html', '/ttt.html', '/chess.html', '/chess_rules.js', '/chess_worker.js', '/flynet.js', '/fly3d.js',
  '/app.webmanifest', '/logo_w.png', '/icons/fly-180.png', '/icons/fly-192.png', '/icons/fly-512.png', '/icons/ttt-192.png', '/vendor/three.r128.min.js',
  '/fonts/Paperlogy-4Regular.woff2', '/fonts/Paperlogy-6SemiBold.woff2', '/fonts/Paperlogy-7Bold.woff2'];
// 신경망 파일은 하나씩 받는다. 하나가 실패해도 설치는 끝나고, 빠진 파일은 체스를 처음 열 때 저장된다
const NET = ['net.json', 'vals.bin', 'col.bin', 'crow.bin', 'bias.bin', 'gain.bin', 'sens.bin', 'ro.bin', 'head.bin', 'npt_idx.bin', 'npt_xyz.bin', 'npt_kind.bin'].map(f => '/net/' + f);
const WAIT = 3000;
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE)
  .then(c => c.addAll(CORE).then(() => Promise.all(NET.map(u => c.add(u).catch(() => {})))))
  .then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const heavy = /\.(png|woff2)$/.test(u.pathname) || /^\/(net|vendor)\//.test(u.pathname);
  const save = res => { if (res.ok || res.type === 'opaque') { const c = res.clone(); caches.open(CACHE).then(k => k.put(e.request, c)); } return res; };
  if (heavy) return e.respondWith(caches.match(e.request).then(r => r || fetch(e.request).then(save)));
  const live = fetch(e.request).then(save);
  const saved = () => caches.match(e.request, { ignoreSearch: true });
  e.waitUntil(live.catch(() => {}));      // 저장본을 먼저 보여 줘도 늦게 온 새 버전은 저장해 둔다
  e.respondWith(new Promise(ok => {
    const t = setTimeout(() => saved().then(r => r && ok(r)), WAIT);   // 저장본이 없으면 계속 네트워크를 기다린다
    live.then(r => { clearTimeout(t); r.ok || r.type === 'opaque' ? ok(r) : saved().then(s => ok(s || r)); }, () => { clearTimeout(t); saved().then(r => ok(r || Response.error())); });
  }));
});
