#!/usr/bin/env bash
# 데스크탑(리눅스·WSL) 세팅: 가상환경 → 연결체 데이터 받기·해시 확인 → 점검
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; M="$ROOT/model"
VENV="${VENV:-$HOME/.venvs/raim-flybrain}"      # 저장소 밖에 둔다 (동기화 폴더에 두면 파일이 숨김 처리돼 깨질 수 있음)

PY=""; for v in python3.13 python3.12 python3.11 python3; do command -v "$v" >/dev/null && { PY="$v"; break; }; done
[ -n "$PY" ] || { echo "Python 3.11 이상을 먼저 설치해 주세요"; exit 1; }
"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Python 3.11 이상이 필요해요"'
echo "1/3 가상환경: $VENV ($("$PY" --version))"
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q -r "$M/requirements.txt"
ln -sfn "$VENV" "$M/.venv"

echo "2/3 연결체 데이터 (처음엔 약 120 MB)"
sha() { "$VENV/bin/python" -c 'import hashlib,sys; h=hashlib.sha256(); f=open(sys.argv[1],"rb"); [h.update(c) for c in iter(lambda: f.read(1<<20), b"")]; print(h.hexdigest())' "$1"; }
get() {  # 파일이름 sha256 주소
  if [ -f "$M/$1" ] && [ "$(sha "$M/$1")" = "$2" ]; then echo "  있음: $1"; return; fi
  echo "  받는 중: $1"; curl -fL --retry 3 -s -o "$M/$1" "$3"
  [ "$(sha "$M/$1")" = "$2" ] || { echo "  [실패] 해시가 달라요: $1"; exit 1; }
}
SHIU=https://raw.githubusercontent.com/philshiu/Drosophila_brain_model/91bdd1e7dcf193f3e7ca5a8933497fcef63b7960
ANN=https://raw.githubusercontent.com/flyconnectome/flywire_annotations/17fc57722002e1a7d38cdd0c89ac382bf92718da/supplemental_files/Supplemental_file1_neuron_annotations.tsv
get 2023_03_23_completeness_630_final.csv e6b71e17671a9bdb05f55e4bc6774640a1418cb7a05125e0fc994ad40f9bfdfb "$SHIU/2023_03_23_completeness_630_final.csv"
get 2023_03_23_connectivity_630_final.parquet 94db8c650533bc36ffa3223f2e62325d5648b8d6bd31c3a4e1c804628c7557b3 "$SHIU/2023_03_23_connectivity_630_final.parquet"
get flywire_annotations_v630.tsv 9a4f8b2f843196074431ebd7cd883536afa1be86c8a4ce90970441e8be81d1be "$ANN"

echo "3/3 점검 (첫 실행은 C 코드 컴파일로 1~2분)"
cd "$M" && "$VENV/bin/python" op_train.py selftest | tail -1 && "$VENV/bin/python" ../desktop/check.py 2>&1 | grep -v -i warn
echo; echo "세팅 끝. 계산 시작: nohup bash $ROOT/desktop/run_octapawn.sh > $ROOT/octapawn.log 2>&1 &"
