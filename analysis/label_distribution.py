"""Label distribution (Table 4) and the share of wrong-source claims among unsupported claims (RQ2).
Unsupported = wrong_source + not_found. Raw shares use counts; weighted shares re-weight each claim by the inverse of
its sampling probability within its submission x stratum, i.e. they estimate the share among all eligible claims
(>= 2 significant digits) of the sampled submissions -- not of the whole benchmark.
usage: python analysis/label_distribution.py"""
import numpy as np, pandas as pd

# development sample: strata = submission x (checker verdict 'supported' in the run the sheet was drawn from)
c = pd.read_csv('labels/claims_to_label.csv'); k = pd.read_csv('labels/claims_to_label_KEY.csv')
lab = pd.read_csv('labels/mosab_labels.csv')
pop = pd.read_csv('data/derived/checker_v0_dev_claims.csv')
pop = pop[pop.sig >= 2].assign(sup0=lambda x: x.L2 == 'supported').groupby(['sub', 'sup0']).size().rename('N')
k = k.merge(c[['id', 'sub']], on='id'); k['sup0'] = k.checker_L2 == 'supported'
n = k.groupby(['sub', 'sup0']).size().rename('n')
w = (pop / n).rename('w').reset_index()
dev = k.merge(w, on=['sub', 'sup0'], how='left').merge(lab[['id', 'label']], on='id')
dev = dev[~dev.id.isin([f'C{i:03d}' for i in range(1, 11)])].assign(sample='development')

# confirmation sample: N_stratum / n_stratum recorded when the sheet was drawn
cf = pd.read_csv('labels/confirm/confirm_claims.csv')
cf = cf.merge(pd.read_csv('labels/confirm/mosab_confirm_labels.csv')[['id', 'label']], on='id')
cf = cf.assign(w=cf.N_stratum / cf.n_stratum, sample='confirmation')

allc = pd.concat([dev[['id', 'sub', 'label', 'w', 'sample']], cf[['id', 'sub', 'label', 'w', 'sample']]], ignore_index=True)
assert allc.w.notna().all(), 'missing sampling weight'
print('submissions with labelled claims:', allc['sub'].nunique(), allc.groupby('sample')['sub'].nunique().to_dict())
print(pd.crosstab(allc.label, allc['sample'], margins=True), '\n')
for name, x in [('development', dev), ('confirmation', cf), ('pooled', allc)]:
    u = x[x.label.isin(['wrong_source', 'not_found'])]; ws = u.label == 'wrong_source'
    print(f'{name:13s} wrong-source / unsupported: raw {ws.sum()}/{len(u)} = {ws.mean():.2f}; '
          f'weighted {np.average(ws, weights=u.w):.2f}')
allc.to_csv('data/derived/labels_with_weights.csv', index=False)
