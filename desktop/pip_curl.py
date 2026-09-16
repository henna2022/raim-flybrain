"""pip 대신 curl로 설치한다. 회사망에서 pip 자체 통신(파이썬 TLS)이 끊길 때 쓴다.
목록도 받기도 전부 curl이라 pip은 마지막에 인터넷 없이 설치만 한다.
사용: python desktop/pip_curl.py torch numpy pandas pyarrow
      INDEX=https://pypi.org/simple python desktop/pip_curl.py ...   (미러 바꾸기)
"""
import hashlib, os, re, subprocess, sys, sysconfig, urllib.parse, zipfile

CACHE = os.path.expanduser('~/.cache/raim-wheels')
INDEX = os.environ.get('INDEX', 'https://pypi.org/simple')   # 국내 미러: https://mirror.kakao.com/pypi/simple
PY = sys.executable
CURL = ['curl', '-sfL', '--http1.1', '--retry', '20', '--retry-all-errors', '--retry-delay', '3', '-m', '1800']
SKIP = ('windows', 'darwin', 'win32', 'ios', 'android')          # 우리는 리눅스(또는 이 기계) 것만 받는다


def tags():
    """이 파이썬이 받을 수 있는 휠 꼬리표. 예: cp314, linux_x86_64 계열"""
    cp = 'cp%d%d' % sys.version_info[:2]
    plat = sysconfig.get_platform().replace('-', '_').replace('.', '_')
    if plat.startswith('linux'):
        arch = plat.split('_', 1)[1]
        return cp, ('manylinux', 'linux_' + arch, arch)
    return cp, (plat.rsplit('_', 2)[0], plat)                    # 맥 등은 대략 맞추기 (점검용)


def ver_key(name):
    """휠 이름에서 버전을 뽑아 숫자로 비교할 수 있게"""
    m = re.match(r'[^-]+-([0-9][^-]*)-', name)
    return [int(x) if x.isdigit() else 0 for x in re.split(r'[._]', m.group(1))] if m else [0]


def best_wheel(pkg, want=None):
    """꾸러미 목록 쪽을 curl로 받아 이 파이썬에 맞는 휠 하나를 고른다.
    want(정확한 버전)가 있고 목록에 있으면 그것을, 없으면 가장 새 것을 고른다"""
    url = f'{INDEX}/{pkg.lower().replace("_", "-")}/'
    page = subprocess.run([*CURL, url], capture_output=True, text=True)
    if page.returncode: return None, None, None
    cp, plats = tags()
    hits = []
    for href, name in re.findall(r'href="([^"]+)"[^>]*>([^<]+\.whl)<', page.stdout):
        low = name.lower()
        if cp not in low and 'py3-none-any' not in low: continue
        if 'py3-none-any' not in low and not any(p in low for p in plats): continue
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
        out.append(re.split(r'[\s<>=!~\[(]', dep.strip())[0])
    return out


if __name__ == '__main__':
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
        queue += [(d, None) for d in needs(path) if d.lower().replace('_', '-') not in seen]
    print(f'받기 끝 ({len(files)}개). 인터넷 없이 설치해요', flush=True)
    subprocess.run([PY, '-m', 'pip', 'install', '--quiet', '--no-index', '--no-deps', *files], check=True)
    print('설치 끝')
