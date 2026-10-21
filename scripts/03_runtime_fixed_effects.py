import json,sys,pandas as pd,numpy as np,statsmodels.formula.api as smf
from scipy import stats
J=sys.argv[1]; H=sys.argv[2]
idx=json.load(open(f'{J}/index.json'))
sub=pd.DataFrame(idx['leaderboard']['submissions'])
sub['G1']=sub['strict'].apply(lambda d:d['G1']).astype(int)
sub['paper']=sub['paper'].astype(int)
tr=pd.read_csv(f'{H}/trajectories/index.csv'); tr['paper']=tr['paper'].str[1:].astype(int); tr=tr.drop(columns=['model']).rename(columns={'agent':'model'})
df=sub.merge(tr[['model','paper','events','attempts','elapsed_hours','completed','bytes']],on=['model','paper'])
df['loghrs']=np.log(df['hours']); df['logev']=np.log(df['events'].clip(lower=1))
df['grpB']=df['paper'].ge(9).astype(int)
print('n=',len(df)); print(df[['hours','elapsed_hours','attempts','events','R_integrity','G1']].describe().round(2).T)
print('\n--- corr(R_integrity, log hours) overall: r=%.3f p=%.4f'%stats.spearmanr(df.loghrs,df.R_integrity)[:2])
print('--- within-agent Spearman (hours vs R_integrity):')
for m,g in df.groupby('model'):
    r,p=stats.spearmanr(g.hours,g.R_integrity); print(f'   {m:16s} rho={r:+.2f} p={p:.2f}  medR={g.R_integrity.median():.1f} medH={g.hours.median():.1f}')
print('\n=== OLS: R_integrity ~ log(hours) + agent FE + paper FE ===')
m1=smf.ols('R_integrity ~ loghrs + C(model) + C(paper)',df).fit(cov_type='HC1')
print(m1.summary().tables[1].as_text().split('\n')[0:4][-1]); 
for k in ['loghrs']: print(f'  {k}: coef={m1.params[k]:+.2f}  p={m1.pvalues[k]:.4f}  (R2={m1.rsquared:.2f})')
print('=== OLS: + attempts + log(events) ===')
m2=smf.ols('R_integrity ~ loghrs + attempts + logev + C(model) + C(paper)',df).fit(cov_type='HC1')
for k in ['loghrs','attempts','logev']: print(f'  {k}: coef={m2.params[k]:+.2f}  p={m2.pvalues[k]:.4f}')
print('=== Logit G1 ~ log(hours) + agent FE, agents with variance only ===')
d3=df[df.model.isin(['astra-6','sol-5.6','opus-5.5'])]
m3=smf.logit('G1 ~ loghrs + C(model)',d3).fit(disp=0)
print(f'  loghrs: coef={m3.params["loghrs"]:+.2f} p={m3.pvalues["loghrs"]:.4f}  n={len(d3)}')
print('=== Group B (2026 papers) vs A: mean R_integrity ===')
print(df.groupby('grpB').R_integrity.mean().round(1).to_dict(), ' G1 pass:',df.groupby('grpB').G1.sum().to_dict())
print('=== per-paper mean R_integrity ===')
print(df.groupby('paper').R_integrity.mean().round(1).to_dict())
df.to_csv('merged.csv',index=False)
