import time, pandas as pd
from brian2 import ms, Hz
from model import run_exp, default_params as P
import utils as utl
config = dict(path_res='./results/try', path_comp='./2023_03_23_completeness_630_final.csv',
              path_con='./2023_03_23_connectivity_630_final.parquet', n_proc=3)
a=pd.read_csv('./flywire_annotations_v630.tsv',sep='\t',low_memory=False)
comp=pd.read_csv(config['path_comp'],index_col=0); a=a[a.root_id.isin(comp.index)]
ct=lambda t,side=None: a[(a.cell_type==t)&((a.side==side) if side else True)].root_id.tolist()
loomR = ct('LPLC2','right')
P['n_run']=3; P['t_run']=1000*ms; P['r_poi']=100*Hz
t0=time.time()
run_exp('loomR', loomR, params=P, force_overwrite=True, **config)
print(f'{time.time()-t0:.0f}s')
df=utl.load_exps(['./results/try/loomR.parquet'])
rate,_=utl.get_rate(df,t_run=P['t_run'],n_run=P['n_run'])
r=rate['loomR']
print('active neurons:', (r>0).sum())
for t in ['DNp01','DNp02','DNp11','DNp03','DNp04','DNp06']:
    ids=[i for i in ct(t) if i in r.index]
    print(t, {i: round(r[i],1) for i in ids})
act=a.set_index('root_id').loc[r[r>0].index.intersection(a.root_id)]
print('\nby super_class:\n', act.super_class.value_counts())
dn=act[act.super_class=='descending']
print('\ndescending neurons firing:', len(dn)); print(pd.Series(r).loc[dn.index].sort_values(ascending=False).head(10).round(1).to_string())
print(dn.cell_type.value_counts().head(10))
