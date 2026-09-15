# 초파리 뇌 모델 로컬 실행 (2026-09-15 확인)
Shiu 외 2024 Nature 연결체 기반 LIF 모델. 원본 github.com/philshiu/Drosophila_brain_model

## 실행
/opt/homebrew/bin/python3.13 -m venv .venv
.venv/bin/pip install brian2 pandas pyarrow joblib
mkdir -p results/try && .venv/bin/python try_all.py

## 2026-09-15 결과 (1초 시뮬 3회 평균, 자극 100 Hz, n_proc 3)
| 자극 | 켜진 뉴런 수 | MN9 좌 (Hz) | MN9 우 (Hz) | 해석 |
|---|---|---|---|---|
| 단맛 | 370 | 67.7 | 48.7 | 주둥이 뻗기 |
| 쓴맛 | 59 | 0 | 0 | 반응 없음 |
| 물 | 86 | 0 | 0 | 100 Hz에서는 반응 없음 |
| 단맛+쓴맛 | 324 | 2.3 | 9.0 | 쓴맛이 단맛 반응 억제 |
소요 시간: 단맛 단독 8초, 4조건 합계 139초 (M-series 맥, 8코어 중 3개)

## 그림자(looming) 자극 (2026-09-15 추가)
뉴런 이름표: flywire_annotations_v630.tsv (github flyconnectome/flywire_annotations). 이 파일은 이름과 달리 783 버전 ID 기준이라, 모델(630 버전) 뉴런 127,400개 중 ID가 두 버전에서 같은 106,214개에만 종류·위치가 붙음. 그래서 감각 뉴런은 16,907개 중 8,126개, 하행 뉴런은 1,303개 중 1,086개, 운동 뉴런은 110개 중 85개만 골라 쓸 수 있음. 시뮬레이션 자체는 127,400개 전부로 돈다.
오른쪽 눈 LPLC2 89개를 100 Hz로 자극 (try_loom.py). 1초 시뮬 3회 78초.
| 읽는 뉴런 | 결과 | 해석 |
|---|---|---|
| DNp01 자이언트 파이버 좌/우 | 124 / 85 Hz | 도망 이륙 명령 |
| DNp04 | 117 Hz | 하행 명령 |
| MDN (문워커) | 켜짐 | 뒷걸음 |
| 하행 뉴런 전체 | 69개 켜짐 | |

## 시각화
export_viz.py → viz/viz.json (배경 뉴런 30% 표본 + 켜진 뉴런 위치, 자극별 첫 trial 스파이크 시각). viz/index.html은 JSON을 안에 박은 단일 파일.
로컬 확인: Desktop/.claude/launch.json의 flybrain-viz (python http.server 8877).
