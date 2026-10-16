/* ────────────────────────────────────────────────────────────────
   전시물 이용 집계 수집기

   각 전시물에 이 파일 하나를 넣고 두 줄만 부르면 됩니다.

     <script src="collect.js"></script>
     <script>RaimCollect.init('language');</script>

   그리고 "한 번 이용했다" 는 지점에서

     RaimCollect.record();               // 기본값 use
     RaimCollect.record('start');        // 시작만 따로 세고 싶을 때
     RaimCollect.record('complete');     // 완주를 따로 세고 싶을 때

   설계 원칙 세 가지
     1. 절대로 전시를 멈추지 않습니다. 무슨 일이 있어도 예외를 밖으로 던지지 않습니다.
     2. 인터넷이 없어도 잃지 않습니다. 기기에 쌓아 두었다가 연결되면 밀어 넣습니다.
        단, 화면을 떠나는 순간 허브가 오류를 내면 그 한 번은 버립니다(두 번 세는 것보다 낫기 때문).
        (언어 연구소처럼 오프라인 전제로 만든 전시물 때문에 반드시 필요합니다)
     3. 개인정보를 보내지 않습니다. 나가는 것은 전시물 이름, 날짜, 사건 이름, 횟수뿐입니다.
        기기 번호도 쿠키도 없습니다.
   ──────────────────────────────────────────────────────────────── */
(function (g) {
  'use strict';

  var HUB = 'https://raim-exhibit-stats.vercel.app/api/collect';
  var QKEY = 'raim-collect-q';
  var MAX_ROWS = 300;      /* 대기열 상한. 넘으면 가장 오래된 것부터 버립니다 */
  var exhibit = '';
  var hub = HUB;
  var sending = false;
  var leaving = false;     /* 화면을 떠나는 중(pagehide). 이때 나는 fetch 실패는 진짜 실패가 아닙니다 */

  function today() {
    var d = new Date();
    return d.getFullYear() + '-' +
           String(d.getMonth() + 1).padStart(2, '0') + '-' +
           String(d.getDate()).padStart(2, '0');
  }

  function loadQ() {
    try {
      var q = JSON.parse(localStorage.getItem(QKEY));
      return Array.isArray(q) ? q : [];
    } catch (e) { return []; }
  }

  function saveQ(q) {
    try { localStorage.setItem(QKEY, JSON.stringify(q)); } catch (e) {}
  }

  /* 같은 (전시물, 날짜, 사건) 은 한 줄로 합쳐 둡니다.
     하루 종일 오프라인이어도 대기열은 몇 줄로 유지됩니다. */
  function push(ev) {
    var q = loadQ();
    var d = today();
    for (var i = 0; i < q.length; i++) {
      if (q[i].exhibit === exhibit && q[i].day === d && q[i].event === ev) {
        q[i].n++;
        saveQ(q);
        return;
      }
    }
    q.push({ exhibit: exhibit, day: d, event: ev, n: 1 });
    if (q.length > MAX_ROWS) q = q.slice(q.length - MAX_ROWS);
    saveQ(q);
  }

  /* 못 보낸 줄을 대기열 앞에 되돌립니다. 그 사이 새로 쌓인 같은 줄과는 횟수를 합칩니다. */
  function putBack(sent) {
    var q = sent.slice(), now = loadQ();
    for (var i = 0; i < now.length; i++) {
      var cur = now[i], hit = false;
      for (var j = 0; j < q.length; j++) {
        if (q[j].exhibit === cur.exhibit && q[j].day === cur.day && q[j].event === cur.event) {
          q[j] = { exhibit: cur.exhibit, day: cur.day, event: cur.event, n: q[j].n + cur.n };
          hit = true; break;
        }
      }
      if (!hit) q.push(cur);
    }
    if (q.length > MAX_ROWS) q = q.slice(q.length - MAX_ROWS);
    saveQ(q);
  }

  function flush() {
    if (sending || !exhibit) return;
    var q = loadQ();
    if (!q.length) return;
    if (g.navigator && g.navigator.onLine === false) return;

    sending = true;
    var sent = q.slice(0, 200);
    /* 보내기 전에 먼저 대기열에서 뺍니다. 카드를 누르면 화면이 바로 넘어가 응답을 못 받는데,
       그때 대기열에 남겨 두면 다음에 홈을 열 때 또 보내서 두 번 세게 됩니다. */
    saveQ(q.slice(200));

    var done = function (ok) {
      sending = false;
      /* 인터넷 끊김·서버 오류(5xx)는 되돌려 두고 다음 기회에.
         단, 화면을 떠날 때 브라우저는 keepalive 요청을 끝까지 보내 주면서도 페이지 쪽엔 "Failed to fetch" 를 줍니다.
         그걸 믿고 되돌리면 두 번 셉니다(크롬에서 확인). */
      if (!ok) { if (!leaving) putBack(sent); return; }
      /* 보내는 동안 새로 쌓인 것이 남아 있으면 이어서 보냅니다.
         이게 없으면 마지막 관람객의 기록이 다음 관람객이 올 때까지 대기열에 묶여 있습니다. */
      if (loadQ().length) setTimeout(flush, 400);
    };

    try {
      g.fetch(hub, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: sent }),
        keepalive: true
      })
        /* 4xx(잘못된 날짜 등)는 다시 보내도 또 거절되므로 버립니다 */
        .then(function (r) { done(r.status < 500); })
        .catch(function () { done(false); });
    } catch (e) {
      done(false);
    }
  }

  g.RaimCollect = {
    /* opts.hub 로 주소를 바꿀 수 있습니다. 보통은 안 씁니다. */
    init: function (key, opts) {
      try {
        exhibit = String(key || '');
        if (opts && opts.hub) hub = opts.hub;
        flush();                                        /* 지난번에 못 보낸 것부터 */
        g.addEventListener('online', flush);            /* 와이파이가 돌아오면 */
        g.addEventListener('pageshow', function () { leaving = false; flush(); });   /* 태블릿을 깨웠을 때 */
        g.addEventListener('pagehide', function () { leaving = true; });
      } catch (e) {}
    },
    record: function (ev) {
      try {
        if (!exhibit) return;
        push(ev === 'start' || ev === 'complete' ? ev : 'use');
        flush();
      } catch (e) {}
    },
    flush: flush,
    /* 확인용. 콘솔에서 RaimCollect.pending() 하면 아직 못 보낸 것이 보입니다. */
    pending: function () { return loadQ(); }
  };
})(typeof window !== 'undefined' ? window : this);
