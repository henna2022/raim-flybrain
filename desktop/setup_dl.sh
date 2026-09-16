#!/usr/bin/env bash
# 딥러닝 체스 첫 관문: 데스크탑(리눅스·WSL)에 PyTorch CUDA 환경을 만들고 그래픽카드 벤치마크를 돌린다.
# 연결체 연결 목록이 없으면 벤치가 알아서 받는다. 사용: bash desktop/setup_dl.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV="${VENV:-$HOME/.venvs/flychess-dl}"

NVSMI=$(command -v nvidia-smi || ls /usr/lib/wsl/lib/nvidia-smi 2>/dev/null || true)   # WSL은 PATH에 없을 때가 있다
[ -n "$NVSMI" ] && "$NVSMI" --query-gpu=name,memory.total,driver_version --format=csv,noheader || echo "nvidia-smi를 못 찾았어요. 계속 진행하고 PyTorch가 직접 확인해요."
# 리눅스(WSL)는 늘 CUDA 12.6용을 깐다 (그래픽카드가 없어도 CPU로 돈다). 맥은 점검용이라 PyPI 기본
# TORCH_INDEX="" 로 두면 PyPI(또는 PIP_INDEX_URL 미러)에서 받는다. PyPI 리눅스 torch도 CUDA 포함본이다.
# 버전을 바꾸려면 TORCH_SPEC="torch==2.13.0"
case "$(uname -s)" in Linux) WHEEL="${TORCH_INDEX---index-url https://download.pytorch.org/whl/cu126}" ;; *) WHEEL="" ;; esac

PY=$(command -v python3.14 || command -v python3.13 || command -v python3.12 || command -v python3.11 || command -v python3 || true)
if [ -z "$PY" ] || ! "$PY" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Python 3.11 이상이 필요해요 (지금: ${PY:-없음})"; exit 1
fi
[ -x "$VENV/bin/python" ] || "$PY" -m venv "$VENV"
"$VENV/bin/python" -m pip install -q --upgrade pip
"$VENV/bin/python" "$ROOT/desktop/pip_resume.py" "${TORCH_SPEC:-torch==2.14.0}" $WHEEL
"$VENV/bin/python" "$ROOT/desktop/pip_resume.py" numpy==2.5.3 pandas==3.0.5 pyarrow==25.0.1

cd "$ROOT"
"$VENV/bin/python" -c "
import shutil, torch
ok = torch.cuda.is_available()
print('torch', torch.__version__, '| CUDA', ok, torch.cuda.get_device_name(0) if ok else '')
if not ok and (shutil.which('nvidia-smi') or shutil.os.path.exists('/usr/lib/wsl/lib/nvidia-smi')): print('[경고] 그래픽카드는 보이는데 PyTorch가 CUDA를 못 써요. 윈도우 NVIDIA 드라이버를 최신으로 올린 뒤 다시 실행하세요. 지금 결과는 CPU 기준이에요.')"
"$VENV/bin/python" -W ignore dl/bench_gpu.py ${BENCH_ARGS:-}
if [ -z "${NO_UPLOAD:-}" ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  TAG="bench-$(date +%Y%m%d-%H%M)"
  gh release create "$TAG" dl/bench_result.json --repo henna2022/raim-flybrain --title "딥러닝 체스 벤치 $TAG" --notes "데스크탑 그래픽카드 벤치 결과" \
    && echo "결과를 GitHub 비공개 저장소 Release $TAG 에 올렸어요. Claude에게 '벤치 끝났어'라고 알려 주세요"
else
  echo "결과 파일: $ROOT/dl/bench_result.json (내용을 Claude에게 붙여 넣어 주세요)"
fi
