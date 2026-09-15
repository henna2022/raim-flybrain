"""딥러닝 체스 첫 관문(D1): 이 컴퓨터에서 연결체 신경망 학습 한 걸음(앞 계산 + 역전파 + AdamW)이 얼마나 걸리고 메모리를 얼마나 쓰나.
사용: python dl/bench_gpu.py [--quick]   (그래픽카드가 있으면 CUDA, 없으면 CPU. --quick은 스크립트 점검용 한 줄만)
결과는 화면과 dl/bench_result.json. 끝에 판정(GO / 조건부 / NO-GO)을 출력한다.

판정 기준 (계획 2026-09-15): 시냅스 >=5 연결, T=10에서 GPU 메모리 80% 이하로 돌린 배치 중 가장 빠른 초당 국면 수 P10
  GO: 기울기 검증 통과 + P10 >= 16   조건부: 9.3 <= P10 < 16 (T=6 허용 시)   NO-GO: 그 밖 (CPU여도 속도로 판정)
  16 = 200만 국면 x 학습 7회 x 1 epoch를 250시간 안에, 9.3 = 같은 조건의 T=6"""
import json, os, platform, sys, time
import numpy as np, pandas as pd, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from conn_op import Conn, conn_matmul, self_test
sys.path.insert(0, os.path.join(HERE, '..', 'desktop'))
from fetch_data import fetch

N, READOUT, SENSORY = 127400, 1171, 8126
LIMIT_S = 60
device = 'cuda' if torch.cuda.is_available() else 'cpu'
sync = torch.cuda.synchronize if device == 'cuda' else (lambda: None)
vram = torch.cuda.get_device_properties(0).total_memory / 2**30 if device == 'cuda' else None
con = pd.read_parquet(fetch('2023_03_23_connectivity_630_final.parquet'),
                      columns=['Presynaptic_Index', 'Postsynaptic_Index', 'Connectivity', 'Excitatory'])
_graphs = {}


def ram_gib():
    try: return os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES') / 2**30
    except (ValueError, AttributeError, OSError): return 16.0   # 윈도우 파이썬에는 sysconf가 없다


def chunk_for(edges, batch):
    """연결 기울기를 계산할 때 배치를 몇 개씩 묶나: 임시 메모리(12바이트 x 묶음 x 연결)를 1 GiB 안으로"""
    return max(1, min(batch, int(2**30 // (12 * edges))))


def est_gib(batch, T, edges, chunk):
    """역전파까지 필요한 메모리 대략치: 단계마다 저장하는 상태 4개 + 연결 기울기 청크 + 그래프·옵티마이저"""
    return (batch * N * T * 4 * 4 + 12 * chunk * edges + 60 * edges) / 2**30


def graph(min_syn):
    if min_syn not in _graphs:
        e = con[con.Connectivity >= min_syn]
        _graphs.clear()                                   # 그래프 하나만 메모리에 둔다
        _graphs[min_syn] = (len(e), Conn(e.Presynaptic_Index.values, e.Postsynaptic_Index.values, N, device),
                            torch.tensor(np.sign(e.Excitatory.values), dtype=torch.float32, device=device),
                            torch.tensor(np.log1p(e.Connectivity.values), dtype=torch.float32, device=device))
    return _graphs[min_syn]


def run(min_syn, batch, T):
    edges, conn, sign, count = graph(min_syn)
    chunk = chunk_for(edges, batch)
    logw = torch.zeros(edges, device=device, requires_grad=True)
    head = torch.nn.Linear(READOUT, 1).to(device)
    opt = torch.optim.AdamW([logw, *head.parameters()], lr=1e-3)
    ro = torch.randint(0, N, (READOUT,), device=device)
    sens = torch.randint(0, N, (SENSORY,), device=device)

    def forward(u):
        vals = sign * count * torch.nn.functional.softplus(logw) * 0.05
        r = torch.zeros(batch, N, device=device)
        for _ in range(T):
            r = r + 0.5 * (-r + torch.relu(conn_matmul(vals, r, conn, chunk) + u))
        return head(r[:, ro])

    train, infer = [], []
    for it in range(3):                                   # 첫 번은 준비 시간이라 버린다
        if device == 'cuda': torch.cuda.reset_peak_memory_stats()
        u = torch.zeros(batch, N, device=device); u[:, sens] = torch.rand(batch, SENSORY, device=device)
        sync(); t0 = time.time()
        loss = forward(u).pow(2).mean(); loss.backward(); opt.step(); opt.zero_grad(set_to_none=True)
        sync(); t1 = time.time()
        with torch.no_grad(): forward(u)
        sync(); t2 = time.time()
        if it: train.append(t1 - t0); infer.append(t2 - t1)
        if t1 - t0 > LIMIT_S: break
    step = float(np.mean(train or [t1 - t0]))
    peak = torch.cuda.max_memory_allocated() / 2**30 if device == 'cuda' else None
    return dict(min_syn=min_syn, edges=edges, batch=batch, T=T, train_step_s=round(step, 3),
                train_positions_per_s=round(batch / step, 1),
                forward_only_positions_per_s=round(batch / float(np.mean(infer or [t2 - t1])), 1),
                peak_gpu_gib=None if peak is None else round(peak, 2),
                fits_80pct_vram=None if peak is None else peak <= 0.8 * vram)


def verdict(info, rows):
    ok = [r for r in rows if r.get('min_syn') == 5 and r.get('T') == 10 and 'train_positions_per_s' in r and r['fits_80pct_vram'] is not False]
    p10 = max((r['train_positions_per_s'] for r in ok), default=0.0)
    hours = round(2e6 * 7 / p10 / 3600) if p10 else None     # 계획 최소치: 200만 국면 x 학습 7회 x 1 epoch
    where = '그래픽카드' if info['device'] == 'cuda' else 'CPU (그래픽카드 없음, 학습 내내 CPU를 다 씀)'
    if not info['gradient_check']:
        return p10, 'NO-GO (기울기 불일치): Claude에게 결과를 보내 주세요'
    if p10 >= 16: return p10, f'GO: {where}로 계획 최소치 약 {hours}시간'
    if p10 >= 9.3: return p10, f'조건부: {where}로 약 {hours}시간. 파일럿에서 T=6이 허용되면 진행, 아니면 대여 GPU'
    return p10, f'NO-GO (너무 느림, 약 {hours}시간): 대여 GPU(RunPod RTX 4090 시간당 약 $0.34)에서 같은 벤치를 돌릴지 결정'


if __name__ == '__main__':
    quick = '--quick' in sys.argv
    info = dict(device=device, torch=torch.__version__, python=platform.python_version(), machine=platform.platform(), cpu_count=os.cpu_count(), ram_gib=round(ram_gib(), 1),
                gpu=torch.cuda.get_device_name(0) if device == 'cuda' else None,
                gpu_total_gib=None if vram is None else round(vram, 1), gradient_check=self_test(device))
    print(info, flush=True)
    plan = [[(5, 32, 10)]] if quick else [
        [(5, 128, 10), (5, 256, 10), (5, 512, 10), (5, 1024, 10)],       # 같은 줄 안에서는 앞 설정이 60초를 넘거나 메모리가 모자라면 뒤는 건너뜀
        [(5, 128, 6)],
        [(3, 128, 10)],
        [(1, 128, 10)],
    ]
    rows = []
    for line in plan:
        for min_syn, batch, T in line:
            edges = int((con.Connectivity >= min_syn).sum()); need = est_gib(batch, T, edges, chunk_for(edges, batch))
            limit = 0.6 * ram_gib() if device == 'cpu' else 0.8 * vram     # CPU에서 모자라면 리눅스가 경고 없이 죽인다
            if need > limit:
                row = dict(min_syn=min_syn, batch=batch, T=T, skipped=f'메모리 약 {need:.1f} GiB 필요, 한도 {limit:.1f} GiB')
                rows.append(row); print(row, flush=True); break
            try:
                row = run(min_syn, batch, T)
            except RuntimeError as ex:
                row = dict(min_syn=min_syn, batch=batch, T=T, error=str(ex)[:200])
                if device == 'cuda': torch.cuda.empty_cache()
            rows.append(row); print(row, flush=True)
            if 'error' in row or row['train_step_s'] > LIMIT_S or row.get('fits_80pct_vram') is False:
                break
    p10, v = verdict(info, rows)
    json.dump(dict(info=info, results=rows, P10=p10, verdict=v), open(os.path.join(HERE, 'bench_result.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print(f'\nP10 (>=5, T=10) = {p10} 국면/초 → {v}')
    print('saved dl/bench_result.json')
