"""틱택토 판 → 초파리 뇌(고정, Shiu 외 2024 LIF 모델) → 하행·운동 뉴런 발화 수.
판은 9글자 'H.F......' (H=사람, F=초파리). 칸 9개 × 돌 2종 = 감각 뉴런 18묶음.
각 감각 뉴런은 논문 방식대로 자기만의 포아송 입력(100 Hz)을 받는다."""
import numpy as np, pandas as pd
from brian2 import (NeuronGroup, Synapses, PoissonGroup, SpikeMonitor, Network,
                    prefs, seed as brian_seed, ms, Hz)
from model import default_params as P

T_RUN, RATE = 200 * ms, 100 * Hz
_net = None

def select(n_groups=18):
    """감각 뉴런을 무작위로 섞어 n_groups 묶음(칸 수 × 2: 틱택토 18, 옥타폰 32)으로 나누고, 읽을 하행·운동 뉴런을 고른다."""
    comp = pd.read_csv('2023_03_23_completeness_630_final.csv', index_col=0)
    ann = pd.read_csv('flywire_annotations_v630.tsv', sep='\t', low_memory=False)
    ann = ann[ann.root_id.isin(comp.index)].drop_duplicates('root_id').set_index('root_id')
    pos = {rid: i for i, rid in enumerate(comp.index)}
    sens = np.random.default_rng(0).permutation(ann[ann.super_class == 'sensory'].index.map(pos).to_numpy())
    cell_of = np.concatenate([np.full(len(g), k) for k, g in enumerate(np.array_split(np.arange(len(sens)), n_groups))])
    ro = ann[ann.super_class.isin(['descending', 'motor'])]
    return dict(comp=comp, ann=ann, sens=sens, cell_of=cell_of, readout=ro.index.map(pos).to_numpy(), readout_ids=ro.index.to_numpy())

def build(target='cython', n_groups=18):
    global _net, stim, mon, cell_of, readout
    prefs.codegen.target = target
    L = select(n_groups); comp, sens, cell_of, readout = L['comp'], L['sens'], L['cell_of'], L['readout']
    con = pd.read_parquet('2023_03_23_connectivity_630_final.parquet')

    neu = NeuronGroup(len(comp), P['eqs'], method='linear', threshold=P['eq_th'],
                      reset=P['eq_rst'], refractory='rfc', namespace=P)
    neu.v = P['v_0']; neu.g = 0; neu.rfc = P['t_rfc']
    neu.rfc[sens] = 0 * ms                      # 감각 뉴런 전체 불응기 0. 논문은 그 시행에 자극받는 뉴런만 0 (알려진 차이, README 참고)
    syn = Synapses(neu, neu, 'w : volt', on_pre='g += w', delay=P['t_dly'])
    syn.connect(i=con.Presynaptic_Index.values, j=con.Postsynaptic_Index.values)
    syn.w = con['Excitatory x Connectivity'].values * P['w_syn']
    stim = PoissonGroup(len(sens), rates=0 * Hz)
    sin = Synapses(stim, neu, on_pre='v += w_in', namespace={'w_in': P['w_syn'] * P['f_poi']})
    sin.connect(i=np.arange(len(sens)), j=sens)
    mon = SpikeMonitor(neu, record=False)
    _net = Network(neu, syn, stim, sin, mon)
    _net.store()

def features(board, seed=0):
    _net.restore()
    n = len(board)
    on = [i for i, c in enumerate(board) if c == 'H'] + [n + i for i, c in enumerate(board) if c == 'F']
    stim.rates = np.isin(cell_of, on) * RATE
    brian_seed(seed)
    _net.run(T_RUN)
    return np.asarray(mon.count)[readout].astype(np.float32)
