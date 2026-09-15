import time
from brian2 import ms
from model import run_exp, default_params as params
import utils as utl

config = dict(path_res='./results/try', path_comp='./2023_03_23_completeness_630_final.csv',
              path_con='./2023_03_23_connectivity_630_final.parquet', n_proc=3)
neu_sugar = [720575940624963786,720575940630233916,720575940637568838,720575940638202345,
 720575940617000768,720575940630797113,720575940632889389,720575940621754367,720575940621502051,
 720575940640649691,720575940639332736,720575940616885538,720575940639198653,720575940620900446,
 720575940617937543,720575940632425919,720575940633143833,720575940612670570,720575940628853239,
 720575940629176663,720575940611875570]
params['n_run'] = 3
params['t_run'] = 1000*ms
t0 = time.time()
run_exp(exp_name='sugarR', neu_exc=neu_sugar, params=params, force_overwrite=True, **config)
print(f'elapsed {time.time()-t0:.0f}s for {params["n_run"]} trials')
df = utl.load_exps(['./results/try/sugarR.parquet'])
rate, std = utl.get_rate(df, t_run=params['t_run'], n_run=params['n_run'])
print('spikes:', len(df), 'active neurons:', (rate['sugarR']>0).sum())
print('MN9 (proboscis motor) rate Hz:', rate.loc[720575940660219265, 'sugarR'])
print(rate.sort_values('sugarR', ascending=False).head(15))
