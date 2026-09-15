#!/usr/bin/env bash
# 딥러닝 체스 첫 관문: 데스크탑(리눅스·WSL)에 PyTorch CUDA 환경을 만들고 그래픽카드 벤치마크를 돌린다.
# 연결체 연결 목록이 없으면 벤치가 알아서 받는다. 사용: bash desktop/setup_dl.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-$HOME/.venvs/flychess-dl}"

if command -v nvidia-smi >/dev/null; then
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  WHEEL="--index-url https://download.pytorch.org/whl/cu126"
else
  echo "nvidia-smi가 없어요. 그래픽카드 드라이버(WSL이면 윈도우 쪽 NVIDIA 드라이버)를 확인하세요. 지금은 CPU로만 잽니다."
  WHEEL="--index-url https://download.pytorch.org/whl/cpu"
fi

PY=$(command -v python3.13 || command -v python3.12 || command -v python3.11 || true)
[ -n "$PY" ] || { echo "Python 3.11 이상이 필요해요"; exit 1; }
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" -m pip install -q torch==2.14.0 $WHEEL
"$VENV/bin/python" -m pip install -q numpy==2.5.3 pandas==3.0.5 pyarrow==25.0.1

cd "$ROOT"
"$VENV/bin/python" -c "
import shutil, torch
ok = torch.cuda.is_available()
print('torch', torch.__version__, '| CUDA', ok, torch.cuda.get_device_name(0) if ok else '')
if not ok and shutil.which('nvidia-smi'): print('[경고] 그래픽카드는 보이는데 PyTorch가 CUDA를 못 써요. 윈도우 NVIDIA 드라이버를 최신으로 올린 뒤 다시 실행하세요. 지금 결과는 CPU 기준이에요.')"
"$VENV/bin/python" -W ignore dl/bench_gpu.py ${BENCH_ARGS:-}
if [ -z "${NO_UPLOAD:-}" ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  TAG="bench-$(date +%Y%m%d-%H%M)"
  gh release create "$TAG" dl/bench_result.json --repo henna2022/raim-flybrain --title "딥러닝 체스 벤치 $TAG" --notes "데스크탑 그래픽카드 벤치 결과" \
    && echo "결과를 GitHub 비공개 저장소 Release $TAG 에 올렸어요. Claude에게 '벤치 끝났어'라고 알려 주세요"
else
  echo "결과 파일: $ROOT/dl/bench_result.json (내용을 Claude에게 붙여 넣어 주세요)"
fi
