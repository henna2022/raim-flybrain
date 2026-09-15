// 화면은 네트워크 먼저(고치면 바로 반영), 끊기면 저장본. 설치 때 두 화면을 미리 저장해 와이파이가 없어도 돌아가게 한다.
const CACHE = 'raim-flybrain-v3';
const CORE = ['/', '/index.html', '/snack.html', '/ttt.html', '/app.webmanifest', '/logo_w.png', '/icons/fly-192.png', '/icons/ttt-192.png', '/fly3d.js', '/vendor/three.r128.min.js',
  '/fonts/Paperlogy-4Regular.woff2', '/fonts/Paperlogy-6SemiBold.woff2', '/fonts/Paperlogy-7Bold.woff2'];
self.addEventListener('install', e => e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting())));
self.addEventListener('activate', e => e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const u = new URL(e.request.url);
  const heavy = /\.(png|woff2)$/.test(u.pathname) || u.pathname.startsWith('/vendor/');
  const save = res => { if (res.ok || res.type === 'opaque') { const c = res.clone(); caches.open(CACHE).then(k => k.put(e.request, c)); } return res; };
  e.respondWith(heavy
    ? caches.match(e.request).then(r => r || fetch(e.request).then(save))
    : fetch(e.request).then(save).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
