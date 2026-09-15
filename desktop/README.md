# 데스크탑에서 돌리기: 출근하면 이 순서대로

**한 줄 요약:** 우분투 설치 → 저장소 받기 → 옥타폰 세팅 → 딥러닝 벤치 → 옥타폰 계산 시작 → Claude에게 알리기.
손이 가는 시간은 1시간 안쪽이고, 옥타폰 계산은 그 뒤 몇 시간 혼자 돈다.

데스크탑: Windows 11, Ryzen 5 9600X, RAM 32 GB, **NVIDIA RTX 4060 8 GB** (2026-09-15 확인)

---

## 0. 시작 전 (2분)

- [ ] 설정 → 시스템 → 전원: 화면 끄기·절전 모드를 **"안 함"**
- [ ] 설정 → Windows 업데이트: **업데이트 1주 일시 중지** (계산 중에 재부팅되면 멈춤)

## 1. 우분투(WSL) 설치 (15분, 재부팅 한 번)

- [ ] 시작 버튼 오른쪽 클릭 → **터미널(관리자)** → 아래 입력
  ```
  wsl --install -d Ubuntu-24.04
  ```
- [ ] 재부팅 → 시작 메뉴에서 **Ubuntu** 열기 → 사용자 이름·비밀번호 만들기 (비밀번호는 쳐도 화면에 안 보이는 게 정상)

이미 깔려 있다고 나오면 바로 Ubuntu를 열면 된다.
권한이 없거나 회사 정책으로 막히면 맨 아래 **플랜 B**로.

## 2. 도구 설치 · GitHub 로그인 · 저장소 받기 (10분)

Ubuntu 창에서 한 줄씩 붙여 넣는다 (붙여넣기는 마우스 오른쪽 클릭).

- [ ] 도구 설치 (비밀번호 물어보면 1번에서 만든 것)
  ```
  sudo apt update && sudo apt install -y git gh curl build-essential python3-dev python3-venv
  ```
- [ ] GitHub 로그인
  ```
  gh auth login --web --git-protocol https
  ```
  → 8자리 코드가 나오면 복사 → 윈도우 브라우저에서 **github.com/login/device** 열고 코드 입력 → henna2022로 승인
- [ ] 저장소 받기
  ```
  cd ~ && gh repo clone henna2022/raim-flybrain
  ```

## 3. 옥타폰 세팅 (5분)

- [ ] 실행
  ```
  bash ~/raim-flybrain/desktop/setup.sh
  ```
- **성공하면:** 마지막에 `===== 데스크탑 점검 결과 =====`가 나오고, 그 아래에 "고속 모드: 됨"과 예상 시간이 보인다
- "맥과 같은 결과"가 3/3이 아니어도 괜찮다 (CPU가 달라서 생기는 작은 차이)

## 4. 딥러닝 벤치 (20~40분, 처음에 약 3 GB 받음)

- [ ] 실행 (이 동안 다른 무거운 프로그램은 끄기)
  ```
  bash ~/raim-flybrain/desktop/setup_dl.sh
  ```
- **성공하면:**
  - 처음에 `NVIDIA GeForce RTX 4060, 8188 MiB` 같은 줄과 `CUDA True`
  - 마지막에 `P10 = ... 국면/초 → GO` (또는 조건부 / NO-GO)
  - `Release bench-... 에 올렸어요`
- `[경고] ... CUDA를 못 써요`가 나오면: 윈도우에서 **NVIDIA App → 드라이버 업데이트** 후 같은 명령 다시

## 5. 옥타폰 계산 시작 (명령 한 줄, 계산은 몇 시간)

- [ ] 실행
  ```
  cd ~/raim-flybrain && nohup bash desktop/run_octapawn.sh > octapawn.log 2>&1 &
  ```
- [ ] 진행 보기 (250판마다 한 줄, `eta`가 남은 분). **Ctrl+C는 보기만 멈추고 계산은 계속된다**
  ```
  tail -f ~/raim-flybrain/octapawn.log
  ```
- [ ] Ubuntu 창은 **닫지 말고 최소화**

## 6. Claude에게 알리기

- 4번이 끝나면: **"벤치 끝났어"**
- 5번 로그 마지막에 `끝`이 나오면: **"옥타폰 결과 올렸어"**
- 막히면: 그 화면 사진

---

## 멈췄을 때

- 컴퓨터가 꺼졌거나 창을 닫았으면: Ubuntu를 다시 열고 **5번 명령을 그대로** 실행 → 끝난 판은 건너뛰고 이어서 돈다
- 어디까지 됐는지:
  ```
  tail -3 ~/raim-flybrain/octapawn.log
  ```

## 플랜 B: 우분투를 못 깔 때 (딥러닝 벤치만)

1. python.org에서 **Python 3.12** 설치. 첫 화면에서 "Add python.exe to PATH" 체크 → Install Now
2. github.com/henna2022/raim-flybrain → **Code → Download ZIP** → 압축 풀기 (폴더 이름 `raim-flybrain-main`)
3. 압축 푼 폴더 중 `desktop`, `dl`, `model` 폴더가 보이는 폴더를 열고, 파일 탐색기 주소창에 `powershell` 입력 → Enter. 열린 창에서 한 줄씩
   ```
   py -3.12 -m venv $HOME\.venvs\flychess-dl
   & $HOME\.venvs\flychess-dl\Scripts\python.exe -m pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cu126
   & $HOME\.venvs\flychess-dl\Scripts\python.exe -m pip install numpy==2.5.3 pandas==3.0.5 pyarrow==25.0.1
   & $HOME\.venvs\flychess-dl\Scripts\python.exe dl\bench_gpu.py
   ```
4. 마지막 `P10 = ...` 줄을 사진으로 보내기. 옥타폰은 맥에서 돌린다

---

## 무엇을 돌리나 (참고)

| 단계 | 파일 | 내용 |
|---|---|---|
| 데이터 | `desktop/fetch_data.py` | 연결체 데이터 받기, SHA-256 확인 |
| 옥타폰 점검 | `desktop/check.py` | 고속 모드, 맥 결과 대조(`reference_op.json`), 판당 시간·작업자 수 |
| 옥타폰 시뮬 | `model/ttt_run.py N W --game=op` | 판마다 감각 뉴런 32묶음 자극, 200 ms, 출력 뉴런 1,171개 발화 수. 난수 0·1 |
| 옥타폰 학습·평가 | `model/op_train.py` | 릿지 판독기, 처음 보는 판 평가, 섞은 대조군 20회, G2 판정 |
| 딥러닝 벤치 | `dl/bench_gpu.py` | 연결체 신경망 학습 한 걸음의 속도·메모리, GO/조건부/NO-GO |
| 연결체 연산 | `dl/conn_op.py` | 연결 모양 그대로 행렬곱과 기울기 (밀집 60 GiB 없이) |

- 가상환경은 저장소 밖(`~/.venvs/`)에 만든다
- 결과는 GitHub 비공개 저장소 Release로 올라간다 (`bench-날짜`, `op-results-날짜`)
- WSL 메모리는 기본으로 윈도우 메모리의 절반(약 15 GB)만 쓴다. 벤치는 넘칠 설정을 미리 건너뛴다
