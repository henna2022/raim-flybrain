# raim-flybrain

서울로봇인공지능과학관 태블릿 전시 "초파리 뇌" 체험. 초파리 연결체 발화 모델(Shiu 외 2024, FlyWire 630 버전)을 고정해 두고, 그 신호로 반응하거나 수를 고른다.

| 화면 | 파일 | 내용 |
|---|---|---|
| 초파리 가상현실과 뇌 | `viz/index.html` | 자극 버튼 → 미리 계산한 뇌 활동 재생 + 가상 초파리 반응 |
| 초파리 뇌와 틱택토 | `viz/ttt.html` | 판마다 미리 계산한 출력 뉴런 발화를 판독기가 점수 매김, 뇌 밖 보조 규칙 2개 |

두 화면 모두 서버 없는 단일 HTML이고, Vercel은 `viz/`만 배포한다.

PWA: 두 화면을 각각 앱으로 설치할 수 있다(`viz/ttt.webmanifest`, `viz/index.webmanifest`, 가로·전체 화면). `viz/sw.js`가 설치 때 두 화면을 저장해 와이파이가 끊겨도 돈다. 화면을 크게 바꿨는데 탭에 안 보이면 `sw.js`의 `CACHE` 이름 숫자를 올린다.

## 다시 만들기
- 연결체 모델 코드와 데이터: https://github.com/philshiu/Drosophila_brain_model (MIT). `2023_03_23_*_630_final.*`, `Completeness_783.csv`, `Connectivity_783.parquet`를 `model/`에 둔다.
- 뉴런 주석표: https://github.com/flyconnectome/flywire_annotations 의 `supplemental_files/Supplemental_file1_neuron_annotations.tsv`를 `model/flywire_annotations_v630.tsv`로 저장 (이름과 달리 783 버전 ID 기준).
- 가상환경은 iCloud 밖에 둔다 (Desktop이 iCloud 동기화면 `.venv` 파일이 숨김 처리돼 Python 3.13이 설정 파일을 건너뜀). 예: `python3.13 -m venv ~/.venvs/raim-flybrain && ln -s ~/.venvs/raim-flybrain model/.venv`
- 틱택토: `ttt_run.py 0`, `ttt_run.py 1` (판 5,477개 시뮬) → `ttt_train.py` (판독기·평가) → `ttt_build_ui.py` (`viz/ttt.html`). 자세한 기록은 `model/README-henna.md`.
