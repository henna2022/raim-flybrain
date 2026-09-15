# 데스크탑에서 옥타폰 계산·학습 돌리기

맥 대신 데스크탑에서 옥타폰 13,854판을 초파리 뇌 모델에 넣고, 판독기 학습과 평가까지 한 번에 돌린다.
결과는 GitHub 비공개 저장소 Release로 올라가서 맥에서 받아 태블릿 화면을 만든다.

## 준비 (한 번만)

**윈도우라면 WSL(윈도우 속 우분투)에서 돌린다.** 윈도우에서 바로 돌리면 C++ 빌드 도구를 따로 깔아야 하고, 없으면 3~4배 느려진다.

1. PowerShell을 관리자로 열고 우분투를 설치한 뒤 재부팅한다.
   ```
   wsl --install -d Ubuntu-24.04
   ```
2. 시작 메뉴에서 Ubuntu를 열고 필요한 도구를 깐다.
   ```
   sudo apt update && sudo apt install -y git gh curl build-essential python3-dev python3-venv
   ```
3. GitHub에 로그인한다. 브라우저가 열리면 henna2022 계정으로 승인.
   ```
   gh auth login --web --git-protocol https
   ```
4. 저장소를 우분투 홈에 받는다. `/mnt/c/...` 같은 윈도우 폴더에 받으면 느리다.
   ```
   cd ~ && gh repo clone henna2022/raim-flybrain
   ```
5. 세팅을 돌린다. 데이터 약 120 MB를 받고 해시를 확인한 뒤, 점검 결과와 예상 시간을 알려 준다.
   ```
   bash ~/raim-flybrain/desktop/setup.sh
   ```

리눅스 데스크탑이면 2번부터 같다 (apt 대신 배포판 패키지 관리자).

## 계산 시작

```
cd ~/raim-flybrain && git pull && nohup bash desktop/run_octapawn.sh > octapawn.log 2>&1 &
```

- 터미널을 닫아도 계속 돈다. 진행은 `tail -f ~/raim-flybrain/octapawn.log` (250판마다 한 줄)
- 윈도우 설정 → 시스템 → 전원에서 **절전 모드를 "안 함"**으로 두고 전원을 연결한다. 컴퓨터가 잠들면 계산이 멈춘다
- 멈췄으면 같은 명령을 다시 실행하면 이어서 돈다
- 작업자 수를 바꾸려면 끝에 숫자: `bash desktop/run_octapawn.sh 12`. 작업자 하나에 메모리 약 1 GB
- WSL은 기본으로 윈도우 메모리의 절반만 쓴다. 작업자를 많이 쓰려면 `C:\Users\<이름>\.wslconfig`에 `[wsl2]` 아래 `memory=24GB`처럼 적고 `wsl --shutdown`

## 끝나면

- 로그 마지막에 평가 결과와 `G2_pass`가 나온다
- 결과 묶음(`op_results.zip`)이 GitHub 비공개 저장소 Release에 자동으로 올라간다. Claude에게 "옥타폰 결과 올렸어"라고 알려 주면 맥에서 받아 화면을 만든다

## 무엇을 돌리나
| 단계 | 파일 | 내용 |
|---|---|---|
| 시뮬 | `model/ttt_run.py N W --game=op` | 판마다 감각 뉴런 32묶음 자극, 200 ms, 출력 뉴런 1,171개 발화 수 저장. 난수 0·1 |
| 학습·평가 | `model/op_train.py` | 릿지 판독기, 처음 보는 판 평가, 섞은 대조군 20회, 새 잡음, 대국 |
| 점검 | `desktop/check.py` | 고속 모드, 맥 결과와 비교(`reference_op.json`), 판당 시간 |
