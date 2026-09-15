"""감각 뉴런 18묶음과 읽는 뉴런(하행·운동) 고르기. ttt_sim.build와 똑같은 규칙이어야 한다."""
import numpy as np, pandas as pd

def select():
    comp = pd.read_csv('2023_03_23_completeness_630_final.csv', index_col=0)
    ann = pd.read_csv('flywire_annotations_v630.tsv', sep='\t', low_memory=False)
    ann = ann[ann.root_id.isin(comp.index)].drop_duplicates('root_id').set_index('root_id')
    pos = {rid: i for i, rid in enumerate(comp.index)}
    sens = np.random.default_rng(0).permutation(ann[ann.super_class == 'sensory'].index.map(pos).to_numpy())
    cell_of = np.concatenate([np.full(len(g), k) for k, g in enumerate(np.array_split(np.arange(len(sens)), 18))])
    ro = ann[ann.super_class.isin(['descending', 'motor'])]
    return dict(comp=comp, ann=ann, sens=sens, cell_of=cell_of,
                readout=ro.index.map(pos).to_numpy(), readout_ids=ro.index.to_numpy())
