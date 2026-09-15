import json, numpy as np, pandas as pd
import utils as utl
a=pd.read_csv('./flywire_annotations_v630.tsv',sep='\t',low_memory=False)
comp=pd.read_csv('./2023_03_23_completeness_630_final.csv',index_col=0)
a=a[a.root_id.isin(comp.index)].dropna(subset=['pos_x']).drop_duplicates('root_id').set_index('root_id')
P=a[['pos_x','pos_y','pos_z']].to_numpy(float)
P=(P-P.mean(0)); P/=np.abs(P).max()
cls={'optic':0,'central':1,'sensory':2,'visual_projection':3,'descending':4,'motor':4,'ascending':1,'sensory_ascending':2,'visual_centrifugal':3,'endocrine':1}
conds=['sugar','bitter','water','sugar+bitter','loomR']
df=utl.load_exps([f'./results/try/{c}.parquet' for c in conds])
df=df[df.trial==0]
active=set(df.flywire_id)&set(a.index)
rng=np.random.default_rng(0)
bg=a.index[rng.random(len(a))<0.3]           # ponytail: 30% background sample, enough for a point cloud
keep=list(dict.fromkeys(list(bg)+list(active)))
idx={rid:i for i,rid in enumerate(keep)}
pos=a.loc[keep,['pos_x','pos_y','pos_z']]; pos=(pos-pos.mean())/np.abs(pos-pos.mean()).max().max()
out={'pos':np.round(pos.to_numpy()*1000).astype(int).tolist(),
     'cls':[cls.get(s,1) for s in a.loc[keep,'super_class']],
     'spk':{}}
for c in conds:
    d=df[(df.exp_name==c)&df.flywire_id.isin(idx)]
    ev=sorted((int(round(t*1000)),idx[f]) for t,f in zip(d.t,d.flywire_id))
    out['spk'][c]=ev
    print(c,'spikes',len(ev),'neurons',d.flywire_id.nunique())
json.dump(out,open('../viz/viz.json','w'),separators=(',',':'))
import os; print('json MB', os.path.getsize('../viz/viz.json')/1e6, 'points', len(keep))
