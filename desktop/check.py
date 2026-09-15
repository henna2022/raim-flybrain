"""데스크탑 점검: 고속(Cython) 모드가 되는지, 맥과 같은 뇌 반응이 나오는지, 판당 시간과 전체 예상 시간.
setup.sh가 마지막에 부른다. 직접 돌릴 때: cd model && .venv/bin/python ../desktop/check.py"""
import os, sys, json, time
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.join(HERE, '..', 'model')); sys.path.insert(0, os.getcwd())
import numpy as np, ttt_sim

try:
    ttt_sim.build('cython', n_groups=32)
    ttt_sim.features('F' * 4 + '.' * 8 + 'H' * 4, 0)          # 첫 호출에 C 코드 컴파일
except Exception as e:
    print('\n[실패] 고속(Cython) 모드를 켜지 못했어요:', repr(e)[:300])
    print('리눅스·WSL이면: sudo apt install -y build-essential python3-dev  후 다시 setup.sh')
    sys.exit(1)

ref = json.load(open(os.path.join(HERE, 'reference_op.json')))
exact, corr = 0, []
for b, counts in ref.items():
    f = ttt_sim.features(b, 0); c = np.array(counts, np.float32)
    exact += int(np.array_equal(f, c)); corr.append(float(np.corrcoef(np.log1p(f), np.log1p(c))[0, 1]))
t0 = time.time()
for b in list(ref) * 2: ttt_sim.features(b, 1)
per = (time.time() - t0) / (2 * len(ref))

cpu = os.cpu_count() or 4
try: ram = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30
except (ValueError, AttributeError, OSError): ram = 16.0
workers = max(1, min(cpu - 1, int(ram // 1.2)))                # 작업자 하나에 메모리 약 0.8~1 GB
hours = 13854 * 2 * per / (workers * 0.8) / 3600               # 0.8: 여러 개 돌릴 때 효율 (추정)
open(os.path.join(HERE, 'workers.txt'), 'w').write(str(workers))

print('\n===== 데스크탑 점검 결과 =====')
print(f'고속 모드: 됨')
print(f'맥과 같은 결과: {exact}/{len(ref)}판 완전히 같음, 상관 {min(corr):.3f} 이상'
      + ('' if exact == len(ref) else '  (CPU·컴파일러 차이로 조금 다를 수 있어요. 한 컴퓨터에서 전부 돌리면 괜찮아요)'))
print(f'판 하나: {per:.2f}초 (작업자 1개)')
print(f'CPU {cpu}개, 메모리 {ram:.0f} GB → 작업자 {workers}개 추천 (desktop/workers.txt에 저장)')
print(f'옥타폰 전체(13,854판 × 난수 2종) 예상: 약 {hours:.1f}시간')
