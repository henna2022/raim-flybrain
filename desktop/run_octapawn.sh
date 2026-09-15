#!/usr/bin/env bash
# 옥타폰 전체 계산(13,854판 × 난수 2종) → 판독기 학습·평가 → 결과 묶기·올리기. 끊겨도 다시 실행하면 이어서 돈다.
# 사용: bash desktop/run_octapawn.sh [작업자 수]   (생략하면 check.py가 추천한 수)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT/model"
PY="$ROOT/model/.venv/bin/python"
W="${1:-$(cat "$ROOT/desktop/workers.txt" 2>/dev/null || echo 4)}"
echo "$(date '+%F %T') 시작, 작업자 $W개"
for s in 0 1; do "$PY" ttt_run.py "$s" "$W" --game=op 2>&1 | grep --line-buffered -v -i warn; done
echo "$(date '+%F %T') 시뮬 끝, 판독기 학습·평가"
"$PY" op_train.py 2>&1 | grep -v -i warn | tail -60
rm -f "$ROOT/op_results.zip"
"$PY" -m zipfile -c "$ROOT/op_results.zip" op/features_seed0.npz op/features_seed1.npz op/readout.json op/fly_moves.json op/report.json
if [ -z "${NO_UPLOAD:-}" ] && command -v gh >/dev/null && gh auth status >/dev/null 2>&1; then
  TAG="op-results-$(date +%Y%m%d-%H%M)"
  gh release create "$TAG" "$ROOT/op_results.zip" --repo henna2022/raim-flybrain --title "옥타폰 계산 결과 $TAG" --notes "데스크탑에서 계산한 발화 수와 판독기" \
    && echo "GitHub 비공개 저장소 Release $TAG 에 올렸어요. Claude에게 '옥타폰 결과 올렸어'라고 알려 주세요"
else
  echo "결과: $ROOT/op_results.zip  (gh 로그인이 안 돼 있어 직접 맥으로 옮겨 주세요)"
fi
echo "$(date '+%F %T') 끝"
