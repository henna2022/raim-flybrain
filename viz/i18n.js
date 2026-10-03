// 한/영 전환. 한국어가 원문이고, 화면에 찍힌 글자를 그 자리에서 영어로 바꾼다.
// 게임 코드는 한국어만 쓰면 되고, 이 파일이 글자 노드와 aria-label 을 지켜보다가 바꿔 준다.
// 선택은 localStorage 'lang' 에 남아 다른 화면으로 넘어가도 유지되고, 80초 손을 안 대면 한국어로 돌아간다. 기본은 한국어.
(function () {
  const EN = {
    // 공통
    '초파리 뇌 탐험': 'Fly Brain Explorer',
    '서울로봇인공지능과학관': 'Seoul Robot & AI Museum',
    '처음으로': 'Home', '설명': 'Help', '시작하기': 'Start', '계속하기': 'Continue', '한 판 더': 'Play again',
    '태블릿이 세로로 되어 있다면': 'If the tablet is upright,', '가로로 세팅해 주세요!': 'please turn it sideways!',
    '이 체험은 가로 화면에서 진행됩니다.': 'This exhibit works in landscape.',
    '손가락으로 돌려 볼 수 있어요': 'Drag with your finger to turn it',
    // 첫 화면
    '오늘은 초파리랑 무엇을 해 볼까요?': 'What shall we do with the fly today?',
    '진짜 초파리 뇌의 연결을 본뜬 컴퓨터 뇌가 여러분에게 반응해요.': 'A computer brain copied from a real fly brain’s wiring reacts to you.',
    '초파리에게 간식 주기': 'Feed the fly a snack',
    '달콤한 설탕, 쓴 먹이, 물을 줘 봐요. 초파리 뇌 속 신경이 어떻게 반짝이는지 볼 수 있어요.': 'Give it sweet sugar, bitter food, or water and watch the neurons in its brain light up.',
    '초파리와 틱택토': 'Tic-tac-toe with the fly',
    '초파리가 뇌 신호로 둘 곳을 골라요. 누가 먼저 세 줄을 만들까요? 한 판 겨뤄 봐요!': 'The fly picks its square from brain signals. Who gets three in a row first? Play a round!',
    '초파리와 체스': 'Chess with the fly',
    '초파리와 한 판 둬 봐요. 초파리가 수를 고르는 동안 뇌가 어떻게 반응하는지 볼 수 있어요.': 'Play a game against the fly and watch its brain react while it chooses a move.',
    '진짜 초파리가 아니라, 초파리 뇌 지도(FlyWire 연결체)로 만든 컴퓨터 모델이에요. 간식 주기와 틱택토의 뇌 반응은 미리 계산해 두었고, 체스는 태블릿이 그 자리에서 계산해요.':
      'This is not a real fly but a computer model built from the FlyWire fly brain map. The snack and tic-tac-toe brain reactions were computed in advance; chess is computed right here on the tablet.',
    // 간식
    '버튼을 눌러 초파리에게 간식을 줘 봐요': 'Tap a button to give the fly a snack',
    '초파리 · 손가락으로 돌려 볼 수 있어요': 'The fly · drag with your finger to turn it',
    '초파리 뇌 속 · 손가락으로 돌려 볼 수 있어요': 'Inside the fly brain · drag with your finger to turn it',
    '초파리에게 무엇을 줘 볼까요? 아래 버튼을 눌러 보세요': 'What shall we give the fly? Tap a button below',
    '눈 신경': 'Eye neurons', '뇌 가운데': 'Brain center', '느끼는 신경': 'Sensing neurons',
    '눈에서 오는 신경': 'From the eyes', '몸에 명령하는 신경': 'Body commands',
    '진짜 초파리 뇌 지도(FlyWire 연결체 630 버전, Shiu 외 2024)로 만든 컴퓨터 모델이에요. 미리 계산한 반응을 천천히 보여 줘요. 말풍선은 반응을 보고 붙인 상상 대사예요.':
      'A computer model built from the real fly brain map (FlyWire connectome v630, Shiu et al. 2024). It replays precomputed reactions slowly. The speech bubbles are made-up lines based on the reaction.',
    '화면에 문제가 생겼어요. 처음으로를 눌러 주세요.': 'Something went wrong on screen. Please tap Home.',
    '이 기기에서는 3D 초파리를 켤 수 없어요. 오른쪽 뇌 활동은 그대로 볼 수 있어요.': 'This device cannot show the 3D fly. You can still watch the brain activity on the right.',
    '달콤한 설탕': 'Sweet sugar', '쓴 먹이': 'Bitter food', '물 한 방울': 'A drop of water', '설탕 + 쓴 먹이': 'Sugar + bitter', '그림자로 놀라게 하기': 'Scare it with a shadow',
    '달콤해! 먹을래!': 'Sweet! I’ll eat it!', '우웩, 안 먹을래.': 'Yuck, no thanks.', '음… 지금은 괜찮아.': 'Hmm… not right now.', '달긴 한데 써…': 'Sweet, but bitter…', '으악, 도망!': 'Eek, run!',
    '주둥이를 뻗게 하는 신경세포(MN9)가 켜졌어요. 그래서 주둥이를 쭉 뻗어요.': 'The neuron that extends the mouthpart (MN9) switched on, so the fly sticks it out.',
    '몸에 명령하는 신경이 거의 조용해요. 주둥이를 뻗지 않아요.': 'The neurons that command the body stay almost silent. No mouthpart extension.',
    '이 정도 물로는 주둥이를 뻗는 신경이 켜지지 않았어요.': 'This much water did not switch on the mouthpart neuron.',
    '쓴맛 신호가 단맛 신호를 눌러서, 주둥이를 거의 안 뻗어요.': 'The bitter signal overrides the sweet one, so the mouthpart barely moves.',
    '도망치라고 명령하는 큰 신경(자이언트 파이버)과 뒤로 걷게 하는 신경이 켜졌어요.': 'The big escape neuron (giant fiber) and the backward-walking neurons switched on.',
    // 틱택토
    '초파리 뇌 신호로 둘 곳을 골라요': 'It picks its square from fly brain signals',
    '내가 먼저': 'I go first', '초파리 먼저': 'Fly goes first',
    '판 모양을 넣는 신경(느끼는 신경)': 'Sensing neurons',
    '반응을 읽는 신경(몸에 명령하는 신경)': 'Command neurons',
    '진짜 초파리 뇌 지도(FlyWire 연결체 630 버전, Shiu 외 2024)로 만든 컴퓨터 모델이에요.': 'A computer model built from the real fly brain map (FlyWire connectome v630, Shiu et al. 2024).',
    '초파리와 한 판 겨뤄 봐요. 규칙은 세 가지예요.': 'Play a round against the fly. There are three rules.',
    '초파리는 빈칸마다 "그 칸에 두면 어떻게 될까"를 뇌에 넣어 보고, 점수가 가장 높은 칸을 골라요. 초파리 뇌라서 더 잘하는 건 아니에요.':
      'For every empty square the fly feeds “what if I play here” into its brain and picks the highest score. Being a fly brain does not make it better.',
    '초파리 뇌가 틱택토를 배운 게 아니라 뇌 밖 판독기가 배웠고, 규칙 도우미가 둘 있어요.': 'The fly brain did not learn tic-tac-toe; a reader outside the brain did, and there are two rule helpers.',
    '규칙 도우미': 'Rule helper',
    '새로 시작할까요?': 'Start over?', '계속할래요': 'Keep playing', '새로 시작해요': 'Start over',
    '실제 뇌 반응, 손가락으로 끌어 입체 회전': 'Real brain reaction, drag to rotate in 3D',
    '왼쪽 위': 'top left', '위': 'top', '오른쪽 위': 'top right', '왼쪽': 'left', '가운데': 'center', '오른쪽': 'right', '왼쪽 아래': 'bottom left', '아래': 'bottom', '오른쪽 아래': 'bottom right',
    '내 차례예요! 빈칸을 콕 눌러 보세요': 'Your turn! Tap an empty square',
    '내가 이겼어요!': 'I won!', '초파리가 이겼어요!': 'The fly won!', '비겼어요!': 'It’s a draw!',
    '초파리: 멋진 한 수였어요!': 'Fly: Nice move!', '초파리: 다음 판도 함께해요!': 'Fly: Let’s play again!', '초파리: 팽팽한 한 판이었어요!': 'Fly: That was a close one!',
    '한 판 더 도전해 볼까요?': 'Want to try again?', '잠깐만요, 초파리 차례예요': 'Hold on, it’s the fly’s turn',
    '뇌 반응을 지켜봐요': 'Watch the brain react', '초파리가 생각하고 있어요': 'The fly is thinking',
    '초파리가 고른 칸이에요 (1 이김 · 0 비김 · -1 짐)': 'The square the fly chose (1 win · 0 draw · -1 loss)',
    '초파리가 수를 고르면 여기에 선택한 칸과 점수가 나와요': 'When the fly picks a square, it shows up here with its score',
    '계산 전': 'not computed', '이 판은 아직 계산 전': 'This board is not computed yet',
    '시작한 뒤 판 아래에서 누가 먼저 둘지 골라요': 'After you start, choose who goes first below the board',
    '빈칸을 콕 눌러 내 동그라미를 놓아요': 'Tap an empty square to place your circle',
    '가로·세로·대각선으로 셋을 먼저 만들면 이겨요': 'Three in a row, column, or diagonal wins',
    // 체스
    '초파리와 체스 | 초파리 뇌 탐험': 'Chess with the fly | Fly Brain Explorer',
    '새 판': 'New game', '내 차례예요! 흰 말을 골라요': 'Your turn! Pick a white piece', '초파리': 'Fly', '나': 'Me',
    '초파리 연결 모양을 본뜬 신경망': 'A neural network shaped like the fly’s wiring',
    '판을 입력하는 신경': 'Board-input neurons', '점수를 읽는 신경': 'Score neurons',
    '밝기 = 실제 계산 반응 · 수마다 최대값 기준': 'Brightness = real computed activity · scaled per move',
    '흰 말을 누르고, 노란 칸을 눌러요': 'Tap a white piece, then a yellow square',
    '점수는 신경망이 계산한 초파리의 승리 가능성이에요.': 'The score is the network’s estimate of the fly’s chance to win.',
    '폰은 끝에 닿으면 자동으로 퀸이 돼요.': 'A pawn that reaches the far end becomes a queen automatically.',
    '초파리 뇌 연결을 본뜬 신경망이 수를 골라요. 앞을 내다보지 않고 한 수만 놓아 봐요.': 'A network copied from the fly brain’s wiring picks the move. It looks only one move ahead.',
    '나는 흰 편, 초파리는 검은 편. 상대 왕이 피할 곳이 없게 만들어요!': 'You are white, the fly is black. Trap the other king so it cannot escape!',
    '나는 흰 편, 초파리는 검은 편': 'You are white, the fly is black',
    '내 흰 말을 눌러요': 'Tap one of your white pieces', '다른 말을 눌러 바꿀 수 있어요': 'Tap another piece to change',
    '노란 칸을 눌러 옮겨요': 'Tap a yellow square to move', '상대 말이 있으면 잡아요': 'If an enemy piece is there, you capture it',
    '초파리가 수를 시험해요': 'The fly tries out its moves', '뇌 반응과 점수를 지켜봐요': 'Watch the brain react and the score',
    '진짜 초파리가 아니라, 뇌의 연결 모양을 본뜬 컴퓨터 신경망이에요.': 'This is not a real fly but a computer network copied from the brain’s wiring.',
    '어른을 위한 설명 · 학습에 안 쓴, 유불리가 뚜렷한 판에서 어느 편이 유리한지 맞힌 비율: 초파리 배선 신경망 69%, 보통 신경망 79%, 판 그대로 계산 75%': 'For grown-ups · Share of unseen positions with a clear advantage where the better side was guessed right: fly-wired network 69%, ordinary network 79%, plain board calculation 75%',
    '초파리 뇌라서 더 잘하는 건 아니에요.': 'Being a fly brain does not make it better.',
    '초파리 뇌를 불러오는 중이에요': 'Loading the fly brain', '뇌 연결 자료 21 MB를 준비하고 있어요.': 'Preparing 21 MB of brain wiring data.',
    '조금만 기다려 주세요': 'Just a moment', '다시 불러오기': 'Reload', '체스판': 'Chessboard',
    '후보 수마다 실제 신경망 활동을 밝기로 표시': 'Real network activity shown as brightness for each candidate move',
    '뇌 자료 준비 진행': 'Brain data loading progress',
    '왕': 'King', '퀸': 'Queen', '룩': 'Rook', '비숍': 'Bishop', '나이트': 'Knight', '폰': 'Pawn',
    '주변 한 칸': 'One square any way', '곧게 · 대각선': 'Straight · diagonal', '가로 · 세로': 'Across · up and down', '대각선': 'Diagonal',
    '두 칸 + 옆 한 칸': 'Two squares + one sideways', '말을 뛰어넘어요': 'Jumps over pieces',
    '앞 한 칸 · 처음 두 칸': 'One forward · two on its first move', '잡을 땐 앞 대각선': 'Captures diagonally forward',
    '이동 가능': 'can move here', '빈칸': 'empty',
    '초파리: 잘했어요! 한 판 더 해요!': 'Fly: Well done! Play again!', '초파리: 졌어요, 한 판 더!': 'Fly: I lost, one more!', '초파리: 팽팽했어요! 한 판 더 해요!': 'Fly: So close! Play again!',
    '체크메이트': 'Checkmate', '스테일메이트': 'Stalemate', '무승부': 'Draw',
    '체크! 내 왕을 안전하게 지켜요': 'Check! Keep your king safe', '체크! 검은 왕이 위험해요': 'Check! The black king is in danger',
    '왕을 피할 곳이 없어요. 흰 편 승리!': 'The king cannot escape. White wins!', '왕을 피할 곳이 없어요. 초파리 승리!': 'The king cannot escape. The fly wins!',
    '움직일 수 없어 비겼어요!': 'No moves left. It’s a draw!', '한참 동안 아무도 잡지 않고 폰도 안 움직여서 비겼어요!': 'Nothing captured and no pawn moved for a long time. It’s a draw!',
    '이 말은 갈 곳이 없어요. 다른 말을 골라요': 'This piece has nowhere to go. Pick another', '갈 곳이 없어요. 다른 말을 골라요': 'has nowhere to go. Pick another',
    '가장 높은 점수의 수를 뒀어요 · 이제 내 차례!': 'It played the highest-scoring move · your turn!',
    '뇌 자료를 가져오지 못했어요': 'Could not load the brain data',
    '다시 불러오기를 눌러 주세요. 계속 안 되면 선생님을 불러 주세요.': 'Please tap Reload. If it keeps failing, ask a staff member.',
    '연결 자료를 준비하고 있어요': 'Preparing the wiring data', '뇌 연결 자료를 차례로 준비하고 있어요': 'Preparing the brain wiring data piece by piece',
  };
  // 숫자·칸 이름이 들어가는 문장은 규칙으로 바꾼다
  const cell = s => EN[s] || s;
  const RULES = [
    [/^명령 신경 ([\d,]+)개 중 ([\d,]+)개가 반짝였어요$/, (m) => `${m[2]} of ${m[1]} command neurons flashed`],
    [/^뇌 속 시간 ([\d.]+)초 · 반짝인 신경세포 ([\d,]+)개$/, (m) => `Brain time ${m[1]} s · ${m[2]} neurons flashed`],
    [/^뇌 점수도 규칙 도우미와 같은 (.+) 칸을 골랐어요$/, (m) => `The brain score also picked the ${cell(m[1])} square, same as the rule helper`],
    [/^뇌 점수로는 (.+) 칸이 1등이었지만, 규칙 도우미가 (바로 이기는|내가 바로 이길) (.+) 칸에 뒀어요$/,
      (m) => `The brain score ranked the ${cell(m[1])} square first, but the rule helper played ${cell(m[3])} to ${m[2] === '바로 이기는' ? 'win right away' : 'block my win'}`],
    [/^(.+) 칸(, 내 돌|, 초파리 돌)?$/, (m) => `${cell(m[1])} square${m[2] === ', 내 돌' ? ', my stone' : m[2] === ', 초파리 돌' ? ', fly’s stone' : ''}`],
    [/^개발용 데이터 · 뇌 계산 ([\d,]+)\/([\d,]+)판$/, (m) => `Dev data · brain computed for ${m[1]}/${m[2]} boards`],
    [/^초파리가 (왕|퀸|룩|비숍|나이트|폰)(?:을|를) 움직였어요$/, (m) => `The fly moved its ${EN[m[1]].toLowerCase()}`],
    [/^초파리가 (왕|퀸|룩|비숍|나이트|폰)(?:으로|로) 내 (왕|퀸|룩|비숍|나이트|폰)(?:을|를) 잡았어요$/, (m) => `The fly took my ${EN[m[2]].toLowerCase()} with its ${EN[m[1]].toLowerCase()}`],
    [/^(체크메이트|스테일메이트|무승부) · 한 판 더 해 볼까요\?$/, (m) => `${EN[m[1]]} · play again?`],
    [/^(왕|퀸|룩|비숍|나이트|폰)의 노란 칸을 골라요 · 다른 말로 바꿔도 돼요$/, (m) => `Tap a yellow square for the ${EN[m[1]].toLowerCase()} · or pick another piece`],
    [/^(왕|퀸|룩|비숍|나이트|폰)\s*(이 말은 )?갈 곳이 없어요\. 다른 말을 골라요$/, (m) => `The ${EN[m[1]].toLowerCase()} has nowhere to go. Pick another`],
    [/^([a-h][1-8]) (흰|검은) (왕|퀸|룩|비숍|나이트|폰)( 이동 가능)?$/, (m) => `${m[1]} ${m[2] === '흰' ? 'white' : 'black'} ${EN[m[3]].toLowerCase()}${m[4] ? ', can move here' : ''}`],
    [/^([a-h][1-8]) 빈칸( 이동 가능)?$/, (m) => `${m[1]} empty${m[2] ? ', can move here' : ''}`],
  ];
  const H1 = { '초파리와 틱택토': 'Fly Tic-tac-toe', '초파리와 체스': 'Fly Chess' };   // 헤더 제목만 짧게 (530 높이에서 안 접히게)
  function translate(ko, tag) {
    const t = ko.trim();
    if (tag === 'H1' && H1[t]) return ko.replace(t, H1[t]);
    if (!/[가-힣]/.test(t)) return ko;
    let en = EN[t];
    if (en === undefined) for (const [re, fn] of RULES) { if (typeof re === 'string') { if (t === re) { en = fn; break; } continue; } const m = t.match(re); if (m) { en = fn(m); break; } }
    if (en === undefined) { missing.add(t); return ko; }
    return ko.replace(t, en);
  }
  const missing = new Set();                 // 영어가 없는 한국어. 콘솔 i18nMissing() 로 볼 수 있다
  window.i18nMissing = () => [...missing];

  const ATTRS = ['aria-label', 'title', 'alt', 'placeholder'];
  let lang = localStorage.getItem('lang') === 'en' ? 'en' : 'ko';
  let applying = false;

  function walk(root, fn) {
    if (root.nodeType === 3) { fn(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 9) return;
    if (root.nodeType === 1) { if (root.tagName === 'SCRIPT' || root.tagName === 'STYLE') return; for (const a of ATTRS) if (root.hasAttribute(a)) fnAttr(root, a); }
    for (const c of root.childNodes) walk(c, fn);
  }
  function fnAttr(el, a) {
    el.__ko = el.__ko || {};
    const cur = el.getAttribute(a);
    if (lang === 'en') { if (el.__ko[a] === undefined || (cur !== el.__en?.[a])) el.__ko[a] = cur; const en = translate(el.__ko[a]); el.__en = el.__en || {}; el.__en[a] = en; if (en !== cur) el.setAttribute(a, en); }
    else if (el.__ko[a] !== undefined && cur !== el.__ko[a]) el.setAttribute(a, el.__ko[a]);
  }
  function fnText(n) {
    const cur = n.nodeValue;
    if (lang === 'en') { if (n.__ko === undefined || cur !== n.__en) n.__ko = cur; const en = translate(n.__ko, n.parentElement && n.parentElement.tagName); n.__en = en; if (en !== cur) n.nodeValue = en; }
    else if (n.__ko !== undefined && cur !== n.__ko) n.nodeValue = n.__ko;
  }
  // 영어는 한국어보다 길어서 헤더가 꽉 찬다. 영어일 때만 헤더 글자를 조금 줄이고 버튼 안에서 줄이 안 접히게 한다
  const CSS = 'html[lang=en] header h1{font-size:20px}html[lang=en] header .sub,html[lang=en] header .tagline,html[lang=en] header>span:not([style]){font-size:13px}'
    + 'html[lang=en] header button,html[lang=en] header a,html[lang=en] header .button,html[lang=en] header .ghost-btn,html[lang=en] header .home,html[lang=en] .lang{white-space:nowrap;font-size:15px;padding-left:12px;padding-right:12px}'
    + 'html[lang=en] .card h2{font-size:22px}html[lang=en] .card p{font-size:15px}';
  function apply() {
    applying = true;
    if (!document.getElementById('i18nStyle')) { const st = document.createElement('style'); st.id = 'i18nStyle'; st.textContent = CSS; document.head.appendChild(st); }
    document.documentElement.lang = lang;
    walk(document.documentElement, fnText);
    const b = document.getElementById('langBtn'); if (b) b.textContent = lang === 'en' ? '한국어' : 'EN';
    mo.takeRecords(); applying = false;
  }
  const mo = new MutationObserver(recs => {
    if (applying) return;
    applying = true;
    for (const r of recs) {
      if (r.type === 'characterData') fnText(r.target);
      else if (r.type === 'attributes') fnAttr(r.target, r.attributeName);
      else for (const n of r.addedNodes) walk(n, fnText);
    }
    mo.takeRecords(); applying = false;
  });
  function start() {
    mo.observe(document.documentElement, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ATTRS });
    apply();
    const b = document.getElementById('langBtn');
    if (b) b.onclick = () => { lang = lang === 'en' ? 'ko' : 'en'; localStorage.setItem('lang', lang); apply(); };
    // 전시 태블릿이라 다음 관람객은 한국어로 시작한다. 80초 손을 안 대면 되돌린다 (화면들의 90초 첫 화면 복귀보다 먼저)
    let idle = 0;
    const touch = () => { clearTimeout(idle); idle = setTimeout(() => { localStorage.removeItem('lang'); if (lang !== 'ko') { lang = 'ko'; apply(); } }, 80000); };
    for (const ev of ['pointerdown', 'keydown']) addEventListener(ev, touch, { capture: true, passive: true });
    touch();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
