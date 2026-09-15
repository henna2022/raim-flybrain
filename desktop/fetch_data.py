"""연결체 데이터 받기와 SHA-256 확인. 리눅스·WSL·윈도우·맥 어디서나 같은 파이썬으로 돈다.
사용: python desktop/fetch_data.py [all|dl]   (dl은 딥러닝 벤치에 필요한 연결 목록 하나만)"""
import hashlib, os, shutil, subprocess, sys, urllib.request

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'model')
SHIU = 'https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960'
ANN = ('https://raw.githubusercontent.com/flyconnectome/flywire_annotations/17fc57722002e1a7d38cdd0c89ac382bf92718da/'
       'supplemental_files/Supplemental_file1_neuron_annotations.tsv')
FILES = {  # 파일 이름: (sha256, 주소)
    '2023_03_23_connectivity_630_final.parquet': ('94db8c650533bc36ffa3223f2e62325d5648b8d6bd31c3a4e1c804628c7557b3', f'{SHIU}/2023_03_23_connectivity_630_final.parquet'),
    '2023_03_23_completeness_630_final.csv': ('e6b71e17671a9bdb05f55e4bc6774640a1418cb7a05125e0fc994ad40f9bfdfb', f'{SHIU}/2023_03_23_completeness_630_final.csv'),
    'flywire_annotations_v630.tsv': ('9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be', ANN),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def fetch(name):
    digest, url = FILES[name]
    path = os.path.join(MODEL, name)
    if os.path.exists(path) and sha256(path) == digest:
        print(f'  있음: {name}')
        return path
    print(f'  받는 중: {name}', flush=True)
    try:   # curl은 리눅스·WSL·맥·윈도우10+에 기본으로 있고 시스템 인증서를 쓴다 (파이썬 urllib은 맥 python.org 빌드에서 인증서 오류)
        if shutil.which('curl'):
            subprocess.run(['curl', '-fsSL', '--retry', '3', '-o', path + '.part', url], check=True)
        else:
            urllib.request.urlretrieve(url, path + '.part')
    except (OSError, subprocess.CalledProcessError) as ex:
        sys.exit(f'  [실패] 받지 못했어요: {name} ({ex})')
    if sha256(path + '.part') != digest:
        os.remove(path + '.part')
        sys.exit(f'  [실패] 해시가 달라요: {name}')
    os.replace(path + '.part', path)
    return path


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for name in (['2023_03_23_connectivity_630_final.parquet'] if which == 'dl' else FILES):
        fetch(name)
    print('데이터 준비 끝')
