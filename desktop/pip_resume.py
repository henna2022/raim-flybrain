"""끊기는 망에서 pip 설치하기. pip은 큰 파일을 이어받지 못해 매번 처음부터 받는다.
그래서 받을 파일 목록을 먼저 뽑고, curl 이어받기로 모두 받은 뒤, 인터넷 없이 설치한다.
사용: python desktop/pip_resume.py [pip install 인자들]
예:   python desktop/pip_resume.py torch==2.14.0 --index-url https://download.pytorch.org/whl/cu126
"""
import json, os, subprocess, sys, tempfile

CACHE = os.path.expanduser('~/.cache/raim-wheels')
PY = sys.executable


def urls_to_download(args):
    with tempfile.TemporaryDirectory() as tmp:
        report = os.path.join(tmp, 'report.json')
        subprocess.run([PY, '-m', 'pip', 'install', '--dry-run', '--quiet', '--report', report, *args], check=True)
        plan = json.load(open(report))
    return [item['download_info']['url'] for item in plan['install']]


def download(url):
    path = os.path.join(CACHE, url.split('/')[-1].split('#')[0])
    print(f'  받는 중: {os.path.basename(path)}', flush=True)
    subprocess.run(['curl', '-fL', '--http1.1', '--retry', '20', '--retry-all-errors', '--retry-delay', '3',
                    '-C', '-', '-o', path, url], check=True)      # 끊겨도 이어받는다
    return path


if __name__ == '__main__':
    os.makedirs(CACHE, exist_ok=True)
    files = [download(u) for u in urls_to_download(sys.argv[1:])]
    if files:
        subprocess.run([PY, '-m', 'pip', 'install', '--quiet', '--no-index', '--no-deps', *files], check=True)
    print(f'설치 끝 ({len(files)}개)')
