"""틱택토 판 → 초파리 뇌(고정, Shiu 외 2024 LIF 모델) → 하행·운동 뉴런 발화 수.
판은 9글자 'H.F......' (H=사람, F=초파리). 칸 9개 × 돌 2종 = 감각 뉴런 18묶음.
각 감각 뉴런은 논문 방식대로 자기만의 포아송 입력(100 Hz)을 받는다."""
import os, numpy as np, pandas as pd
from brian2 import (NeuronGroup, Synapses, PoissonGroup, SpikeMonitor, Network,
                    prefs, seed as brian_seed, ms, Hz)
from model import default_params as P

FILES = {'630': ('2023_03_23_completeness_630_final.csv', '2023_03_23_connectivity_630_final.parquet'),
         '783': ('Completeness_783.csv', 'Connectivity_783.parquet')}
V = os.environ.get('FLYWIRE', '630')   # FLYWIRE=783 이면 783 배선. 작업자 프로세스에도 그대로 전해진다
SENS = os.environ.get('FLYWIRE_SENS', V)   # FLYWIRE_SENS=630: 783 배선에 630에서 쓰던 감각 뉴런·묶음만 넣는 대조(입력 세기 맞춤)
SHUF = int(os.environ.get('FLYWIRE_SHUF', 0))   # FLYWIRE_SHUF=1: 감각 뉴런을 묶음에 나누는 무작위 순서만 바꾼 대조(묶음 운)
COMP, CON = FILES[V]
OUT = ('' if V == '630' else V) + ('' if SENS == V else 's' + SENS) + (f'g{SHUF}' if SHUF else '')   # 결과 폴더 꼬리: ttt/ → ttt783/ · ttt783s630/ · ttt783g1/
T_RUN, RATE = 200 * ms, 100 * Hz
_net = None

def select(n_groups=18):
    """감각 뉴런을 무작위로 섞어 n_groups 묶음(칸 수 × 2: 틱택토 18, 옥타폰 32)으로 나누고, 읽을 하행·운동 뉴런을 고른다."""
    comp = pd.read_csv(COMP, index_col=0)
    ann_all = pd.read_csv('flywire_annotations_v630.tsv', sep='\t', low_memory=False)
    ann = ann_all[ann_all.root_id.isin(comp.index)].drop_duplicates('root_id').set_index('root_id')
    pos = {rid: i for i, rid in enumerate(comp.index)}
    sc = comp if SENS == V else pd.read_csv(FILES[SENS][0], index_col=0)   # 감각 뉴런을 고르는 버전
    sa = ann_all[ann_all.root_id.isin(sc.index)].drop_duplicates('root_id').set_index('root_id')
    spos = {rid: i for i, rid in enumerate(sc.index)}
    sens = np.random.default_rng(SHUF).permutation(sa[sa.super_class == 'sensory'].index.map(spos).to_numpy())
    sens = sc.index[sens].map(pos).to_numpy()                             # 고른 버전의 순서 그대로, 지금 배선의 번호로
    cell_of = np.concatenate([np.full(len(g), k) for k, g in enumerate(np.array_split(np.arange(len(sens)), n_groups))])
    ro = ann[ann.super_class.isin(['descending', 'motor'])]
    return dict(comp=comp, ann=ann, sens=sens, cell_of=cell_of, readout=ro.index.map(pos).to_numpy(), readout_ids=ro.index.to_numpy())

def build(target='cython', n_groups=18):
    global _net, stim, mon, cell_of, readout
    prefs.codegen.target = target
    L = select(n_groups); comp, sens, cell_of, readout = L['comp'], L['sens'], L['cell_of'], L['readout']
    con = pd.read_parquet(CON)

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
