"""pip 대신 curl로 설치한다. 회사망에서 pip 자체 통신(파이썬 TLS)이 끊길 때 쓴다.
목록도 받기도 전부 curl이라 pip은 마지막에 인터넷 없이 설치만 한다.
사용: python desktop/pip_curl.py torch numpy pandas pyarrow
      INDEX=https://pypi.org/simple python desktop/pip_curl.py ...   (미러 바꾸기)
"""
import hashlib, os, platform, re, subprocess, sys, urllib.parse, zipfile

CACHE = os.path.expanduser('~/.cache/raim-wheels')
INDEX = os.environ.get('INDEX', 'https://pypi.org/simple')   # 국내 미러: https://mirror.kakao.com/pypi/simple
PY = sys.executable
CURL = ['curl', '-sfL', '--http1.1', '--retry', '20', '--retry-all-errors', '--retry-delay', '3', '-m', '1800']
SKIP = ('windows', 'darwin', 'win32', 'ios', 'android')          # 우리는 리눅스(또는 이 기계) 것만 받는다


def tags():
    """이 파이썬이 받을 수 있는 꼬리표. cp314는 보통 파이썬, cp314t는 다른 종류라 섞으면 안 된다"""
    cp = 'cp%d%d' % sys.version_info[:2]
    osname = {'linux': 'linux', 'darwin': 'macosx', 'win32': 'win'}.get(sys.platform, sys.platform)
    return cp, platform.machine(), osname      # 리눅스 x86_64, 맥 arm64 처럼 기계 종류를 직접 본다


def fits(name, cp, arch, osname):
    """휠 이름 끝의 꼬리표 세 개(파이썬·ABI·플랫폼)가 이 기계에 맞나"""
    part = name[:-4].split('-')
    if len(part) < 5: return False
    pyt, abit, plat = part[-3], part[-2], part[-1]
    if not any(t == cp or t == 'py3' or t == 'py2' for t in pyt.split('.')): return False
    if abit not in ('none', 'abi3', cp): return False          # cp314t 같은 다른 ABI를 막는다
    if plat == 'any': return True
    ok = [p for p in plat.split('.') if p.endswith(arch)]
    if not ok: return False
    if osname == 'linux':
        return any(p.startswith(('manylinux', 'linux')) for p in ok)   # musllinux 제외
    return any(p.startswith(osname) for p in ok)


def ver_key(name):
    """휠 이름에서 버전을 뽑는다. 정식판이 시험판(rc·a·b·dev)보다 앞선다"""
    m = re.match(r'[^-]+-([^-]+)-', name)
    v = m.group(1) if m else '0'
    stable = 0 if re.search(r'(a|b|rc|dev)\d*$', v) else 1
    return (stable, [int(x) for x in re.findall(r'\d+', v)])


def best_wheel(pkg, want=None):
    """꾸러미 목록 쪽을 curl로 받아 이 파이썬에 맞는 휠 하나를 고른다.
    want(정확한 버전)가 있고 목록에 있으면 그것을, 없으면 가장 새 것을 고른다"""
    url = f'{INDEX}/{pkg.lower().replace("_", "-")}/'
    page = subprocess.run([*CURL, url], capture_output=True, text=True)
    if page.returncode: return None, None, None
    cp, arch, osname = tags()
    hits = []
    for href, name in re.findall(r'href="([^"]+)"[^>]*>([^<]+\.whl)<', page.stdout):
        if not fits(name, cp, arch, osname): continue
        link, _, frag = href.partition('#')
        sha = frag.split('=')[1] if frag.startswith('sha256=') else None
        hits.append((ver_key(name), name, urllib.parse.urljoin(url, link), sha))   # 목록의 주소는 상대 경로다
    if not hits: return None, None, None
    if want:                                                      # 이미 받아 둔 버전이 있으면 그것을 맞춘다
        exact = [h for h in hits if re.match(rf'[^-]+-{re.escape(want)}-', h[1])]
        if exact: hits = exact
    _, name, link, sha = max(hits)
    return name, link, sha


def ok_file(path, sha):
    """목록에 적힌 해시와 같고 zip으로 열리면 온전한 파일이다"""
    if not os.path.exists(path) or not zipfile.is_zipfile(path): return False
    if not sha: return True
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''): h.update(blk)
    return h.hexdigest() == sha


def fetch(pkg, want=None):
    name, href, sha = best_wheel(pkg, want)
    if not name:
        print(f'  건너뜀: {pkg} (맞는 휠이 없어요)', flush=True)
        return None
    path = os.path.join(CACHE, name)
    if ok_file(path, sha):
        print(f'  있음: {name}', flush=True)                       # 아침에 받아 둔 것을 그대로 쓴다
        return path
    print(f'  받는 중: {name}', flush=True)
    if subprocess.run([*CURL, '-C', '-', '-o', path, href]).returncode:   # 끊겨도 이어받는다
        sys.exit(f'  [실패] 못 받았어요: {name}. 다시 실행하면 이어받아요')
    if not ok_file(path, sha):
        os.remove(path)
        sys.exit(f'  [실패] 파일이 깨졌어요: {name}. 다시 실행하면 처음부터 받아요')
    return path


def needs(path):
    """받은 휠 안의 METADATA에서 같이 깔아야 할 꾸러미 이름을 뽑는다"""
    with zipfile.ZipFile(path) as z:
        meta = next((n for n in z.namelist() if n.endswith('.dist-info/METADATA')), None)
        if not meta: return []
        lines = z.read(meta).decode('utf-8', 'replace').splitlines()
    out = []
    for l in lines:
        if not l.startswith('Requires-Dist:'): continue
        req = l.split(':', 1)[1].strip()
        dep, _, marker = req.partition(';')
        if 'extra ==' in marker: continue                        # 선택 기능은 안 깐다
        if any(s in marker.lower() for s in SKIP): continue       # 다른 운영체제 것은 안 깐다
        dep = dep.strip()
        name = re.split(r'[\s<>=!~\[(]', dep)[0]
        m = re.search(r'==\s*([0-9][^\s,;]*)', dep)              # torch가 못 박은 버전을 그대로 따른다
        out.append((name, m.group(1) if m else None))
    return out


def selftest():
    cp, arch, osname = 'cp314', 'x86_64', 'linux'
    good = ['torch-2.14.0-cp314-cp314-manylinux_2_28_x86_64.whl',
            'nvidia_cudnn_cu13-9.24.0.43-py3-none-manylinux_2_27_x86_64.whl',
            'markupsafe-3.0.3-cp314-cp314-manylinux_2_17_x86_64.manylinux2014_x86_64.whl',
            'filelock-3.32.7-py3-none-any.whl']
    bad = ['torch-2.14.0-cp314-cp314t-manylinux_2_28_x86_64.whl',        # 다른 종류의 파이썬
           'markupsafe-3.0.3-cp314-cp314t-musllinux_1_2_x86_64.whl',     # 다른 리눅스
           'torch-2.14.0-cp313-cp313-manylinux_2_28_x86_64.whl',         # 다른 파이썬 판
           'torch-2.14.0-cp314-cp314-win_amd64.whl',                     # 윈도우
           'numpy-2.5.3-cp314-cp314-macosx_11_0_arm64.whl']              # 맥
    for n in good: assert fits(n, cp, arch, osname), n
    for n in bad: assert not fits(n, cp, arch, osname), n
    assert fits('numpy-2.5.3-cp314-cp314-macosx_11_0_arm64.whl', 'cp314', 'arm64', 'macosx')   # 맥에서도 골라야 한다
    assert ver_key('sympy-1.14.0-py3-none-any.whl') > ver_key('sympy-1.14.0rc2-py3-none-any.whl')   # 정식판 우선
    assert ver_key('nvidia_cudnn_cu13-9.24.0.43-py3-none-manylinux_2_27_x86_64.whl') > \
           ver_key('nvidia_cudnn_cu13-0.0.0a0-py2.py3-none-any.whl')     # 껍데기 꾸러미를 안 고른다
    print('selftest ok | 맞는 이름', len(good), '개, 거르는 이름', len(bad), '개')


if __name__ == '__main__':
    if sys.argv[1:2] == ['selftest']: selftest(); sys.exit()
    os.makedirs(CACHE, exist_ok=True)
    # pip 인자를 그대로 받아도 되게 옵션·주소는 버리고 버전 못은 떼어 낸다 (목록에서 가장 새 것을 받는다)
    # pip 인자를 그대로 받아도 되게 옵션·주소는 버린다. pkg==버전은 그 버전을 그대로 노린다
    queue = []
    for a in sys.argv[1:]:
        if a.startswith(('-', 'http')): continue
        pkg, eq, ver = a.partition('==')
        queue.append((re.split(r'[\s<>=!~\[(]', pkg)[0], ver if eq and ver[:1].isdigit() else None))
    seen, files = set(), []
    if not queue: sys.exit('설치할 꾸러미 이름을 적어 주세요. 예: python desktop/pip_curl.py torch')
    while queue:
        pkg, want = queue.pop(0)
        key = pkg.lower().replace('_', '-')
        if key in seen: continue
        seen.add(key)
        path = fetch(pkg, want)
        if not path: continue
        files.append(path)
        queue += [(d, v) for d, v in needs(path) if d.lower().replace('_', '-') not in seen]
    if not files: sys.exit('  [실패] 맞는 휠을 하나도 못 찾았어요. 꾸러미 이름과 파이썬 판을 확인해 주세요')
    print(f'받기 끝 ({len(files)}개). 인터넷 없이 설치해요', flush=True)
    subprocess.run([PY, '-m', 'pip', 'install', '--quiet', '--no-index', '--no-deps', *files], check=True)
    print('설치 끝')
