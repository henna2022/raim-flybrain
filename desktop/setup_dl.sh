#!/usr/bin/env bash
# 딥러닝 체스 첫 관문: 데스크탑(리눅스·WSL)에 PyTorch CUDA 환경을 만들고 그래픽카드 벤치마크를 돌린다.
# 먼저 setup.sh를 한 번 돌려 연결체 데이터를 받아 둘 것. 사용: bash desktop/setup_dl.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-$HOME/.venvs/flychess-dl}"
[ -f "$ROOT/model/2023_03_23_connectivity_630_final.parquet" ] || { echo "연결체 데이터가 없어요. 먼저 bash desktop/setup.sh"; exit 1; }

if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  WHEEL="--index-url https://download.pytorch.org/whl/cu126"
else
  echo "nvidia-smi가 없어요. 그래픽카드 드라이버(WSL이면 윈도우 쪽 NVIDIA 드라이버)를 확인하세요. 지금은 CPU로만 잽니다."
  WHEEL="--index-url https://download.pytorch.org/whl/cpu"
fi

PY=""; for v in python3.13 python3.12 python3.11; do command -v "$v" >/dev/null && { PY="$v"; break; }; done
[ -n "$PY" ] || { echo "Python 3.11 이상이 필요해요"; exit 1; }
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q torch==2.14.0 $WHEEL
"$VENV/bin/python" -m pip install -q numpy==2.5.3 pandas==3.0.5 pyarrow==25.0.1

cd "$ROOT"
"$VENV/bin/python" -c "import torch; print('torch', torch.__version__, '| CUDA', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
"$VENV/bin/python" -W ignore dl/bench_gpu.py
echo; echo "끝. dl/bench_result.json 내용을 Claude에게 붙여 넣어 주세요:"; cat dl/bench_result.json
