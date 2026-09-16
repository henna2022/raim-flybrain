"""끊기는 망에서 pip 설치하기. pip은 큰 파일을 이어받지 못해 매번 처음부터 받는다.
그래서 받을 파일 목록을 먼저 뽑고, curl 이어받기로 모두 받은 뒤, 인터넷 없이 설치한다.
사용: python desktop/pip_resume.py [pip install 인자들]
예:   python desktop/pip_resume.py torch==2.14.0 --index-url https://download.pytorch.org/whl/cu126
"""
import json, os, subprocess, sys, tempfile, time

CACHE = os.path.expanduser('~/.cache/raim-wheels')
PY = sys.executable


MIRROR = 'https://mirror.kakao.com/pypi/simple'      # 국내 미러. 회사망이 해외 TLS를 끊을 때 쓴다


def urls_to_download(args, tries=6):
    """받을 파일 목록만 pip에게 묻는다. 이 단계는 pip 자체 통신이라 회사망에서 끊기기 쉬워 여러 번 시도한다."""
    for i in range(tries):
        extra = [] if i < tries - 2 else ['--index-url', MIRROR]   # 끝 두 번은 국내 미러로 바꿔 본다
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, 'report.json')
            r = subprocess.run([PY, '-m', 'pip', 'install', '--dry-run', '--quiet', '--retries', '10',
                                '--timeout', '60', '--report', report, *args, *extra], capture_output=True, text=True)
            if r.returncode == 0:
                return [item['download_info']['url'] for item in json.load(open(report))['install']]
        where = '국내 미러' if extra else '기본 주소'
        print(f'  목록 받기 실패 ({where}, {i + 1}/{tries}회). 다시 시도해요', flush=True)
        time.sleep(3)
    sys.exit('  [실패] 받을 목록을 가져오지 못했어요. 망이 계속 끊기면 desktop/README.md 의 플랜 B를 보세요:\n'
             '         PIP_INDEX_URL=https://mirror.kakao.com/pypi/simple TORCH_INDEX="" bash desktop/setup_dl.sh')


def remote_size(url):
    """서버가 말하는 파일 크기. 못 알아내면 0"""
    out = subprocess.run(['curl', '-sIL', '--http1.1', '-m', '30', url], capture_output=True, text=True).stdout
    sizes = [int(l.split(':', 1)[1]) for l in out.splitlines() if l.lower().startswith('content-length')]
    return max(sizes, default=0)


def download(url):
    path = os.path.join(CACHE, url.split('/')[-1].split('#')[0])
    want = remote_size(url)
    if want and os.path.exists(path) and os.path.getsize(path) == want:
        print(f'  있음: {os.path.basename(path)}', flush=True)      # 다 받아 둔 것을 또 받지 않는다
        return path
    print(f'  받는 중: {os.path.basename(path)}', flush=True)
    subprocess.run(['curl', '-fL', '--http1.1', '--retry', '20', '--retry-all-errors', '--retry-delay', '3',
                    '-C', '-', '-o', path, url], check=True)      # 끊겨도 이어받는다
    if want and os.path.getsize(path) != want:
        sys.exit(f'  [실패] 크기가 달라요: {os.path.basename(path)} ({os.path.getsize(path)} != {want}). 다시 실행하면 이어받아요')
    return path


if __name__ == '__main__':
    os.makedirs(CACHE, exist_ok=True)
    files = [download(u) for u in urls_to_download(sys.argv[1:])]
    if files:
        subprocess.run([PY, '-m', 'pip', 'install', '--quiet', '--no-index', '--no-deps', *files], check=True)
    print(f'설치 끝 ({len(files)}개)')
