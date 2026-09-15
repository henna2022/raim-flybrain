"""딥러닝 체스 첫 관문: 이 컴퓨터에서 연결체 신경망 한 번 학습(앞 계산 + 역전파)이 얼마나 걸리고 메모리를 얼마나 쓰나.
사용: python dl/bench_gpu.py            (그래픽카드가 있으면 CUDA, 없으면 CPU)
결과는 화면과 dl/bench_result.json. 이 파일을 Claude에게 알려 주면 학습 시간을 계산한다."""
import json, os, platform, sys, time
import numpy as np, pandas as pd, torch

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from conn_op import Conn, conn_matmul, self_test

N, READOUT, SENSORY = 127400, 1171, 8126
device = 'cuda' if torch.cuda.is_available() else 'cpu'
sync = torch.cuda.synchronize if device == 'cuda' else (lambda: None)
con = pd.read_parquet(os.path.join(HERE, '..', 'model', '2023_03_23_connectivity_630_final.parquet'),
                      columns=['Presynaptic_Index', 'Postsynaptic_Index', 'Connectivity', 'Excitatory'])


def step_time(min_syn, batch, T, chunk):
    e = con[con.Connectivity >= min_syn]
    conn = Conn(e.Presynaptic_Index.values, e.Postsynaptic_Index.values, N, device)
    sign = torch.tensor(np.sign(e.Excitatory.values), dtype=torch.float32, device=device)
    count = torch.tensor(np.log1p(e.Connectivity.values), dtype=torch.float32, device=device)
    logw = torch.zeros(len(e), device=device, requires_grad=True)
    head = torch.nn.Linear(READOUT, 1).to(device)
    ro = torch.randint(0, N, (READOUT,), device=device)
    sens = torch.randint(0, N, (SENSORY,), device=device)
    times = []
    for it in range(3):                                  # 첫 번은 준비 시간이라 버린다
        if device == 'cuda': torch.cuda.reset_peak_memory_stats()
        u = torch.zeros(batch, N, device=device)
        u[:, sens] = torch.rand(batch, SENSORY, device=device)
        sync(); t0 = time.time()
        vals = sign * count * torch.nn.functional.softplus(logw) * 0.05
        r = torch.zeros(batch, N, device=device)
        for _ in range(T):
            r = r + 0.5 * (-r + torch.relu(conn_matmul(vals, r, conn, chunk) + u))
        loss = head(r[:, ro]).pow(2).mean()
        sync(); t1 = time.time()
        loss.backward()
        sync(); t2 = time.time()
        logw.grad = None
        if it: times.append((t1 - t0, t2 - t1))
    fwd, bwd = np.mean(times, axis=0)
    peak = torch.cuda.max_memory_allocated() / 2**30 if device == 'cuda' else None
    return dict(min_syn=min_syn, edges=len(e), batch=batch, T=T, forward_s=round(float(fwd), 3), backward_s=round(float(bwd), 3),
                positions_per_s=round(batch / float(fwd + bwd), 1), peak_gpu_gib=None if peak is None else round(peak, 2),
                hours_per_million_positions=round(1e6 / (batch / float(fwd + bwd)) / 3600, 2))


if __name__ == '__main__':
    info = dict(device=device, torch=torch.__version__, python=platform.python_version(), machine=platform.platform(),
                gpu=torch.cuda.get_device_name(0) if device == 'cuda' else None,
                gpu_total_gib=round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1) if device == 'cuda' else None,
                gradient_check=self_test(device))
    print(info, flush=True)
    rows = []
    configs = [(5, 32, 10), (5, 128, 10), (3, 32, 10), (3, 128, 10), (1, 32, 10)]
    for min_syn, batch, T in configs:
        try:
            row = step_time(min_syn, batch, T, chunk=8 if device == 'cpu' else 32)
        except RuntimeError as ex:                         # 메모리 부족이면 기록하고 다음으로
            row = dict(min_syn=min_syn, batch=batch, T=T, error=str(ex)[:200])
            if device == 'cuda': torch.cuda.empty_cache()
        rows.append(row); print(row, flush=True)
    json.dump(dict(info=info, results=rows), open(os.path.join(HERE, 'bench_result.json'), 'w'), indent=1)
    print('saved dl/bench_result.json')
