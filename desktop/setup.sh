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
"$VENV/bin/python" "$ROOT/desktop/fetch_data.py" all

echo "3/3 점검 (첫 실행은 C 코드 컴파일로 1~2분)"
cd "$M" && "$VENV/bin/python" op_train.py selftest | tail -1 && "$VENV/bin/python" ../desktop/check.py 2>&1 | grep -v -i warn
echo; echo "세팅 끝. 계산 시작: nohup bash $ROOT/desktop/run_octapawn.sh > $ROOT/octapawn.log 2>&1 &"
