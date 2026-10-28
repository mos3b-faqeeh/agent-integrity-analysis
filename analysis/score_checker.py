"""Score the claim-to-evidence checker against Mosab's human labels.
usage: python analysis/score_checker.py <checker_output_csv>
Positive class = human label 'traceable'. 'not_a_claim' rows are dropped (extraction errors are reported separately).
Population estimates re-weight each labelled claim by 1/P(sampled) within its (submission x checker-verdict) stratum.
CIs: cluster bootstrap over submissions (2,000 resamples)."""
import sys, numpy as np, pandas as pd
cc = pd.read_csv(sys.argv[1])
c = pd.read_csv('labels/claims_to_label.csv'); k = pd.read_csv('labels/claims_to_label_KEY.csv')
lab = pd.read_csv('labels/mosab_labels.csv')
d = c[['id', 'sub', 'kind', 'claim', 'paper_context']].merge(k[['id', 'split']], on='id').merge(lab[['id', 'label']], on='id')
cc = cc[cc.sig >= 2].copy(); cc['ctx'] = cc.context.astype(str).str[:500]
d['ctx'] = d.paper_context.astype(str)
j = d.merge(cc, left_on=['sub', 'claim', 'ctx'], right_on=['sub', 'raw', 'ctx'], how='left', suffixes=('', '_cc'))
j = j.drop_duplicates('id')
assert j.L2.notna().all(), j[j.L2.isna()].id.tolist()
# sampling weights: stratum = sub x (checker L2 == supported) in the ORIGINAL checker run the sheet was drawn from
k2 = k.merge(c[['id', 'sub']], on='id'); k2['sup0'] = k2.checker_L2 == 'supported'
pop = pd.read_csv(sys.argv[2]) if len(sys.argv) > 2 else cc
pop = pop[pop.sig >= 2]; pop = pop.assign(sup0=pop.L2 == 'supported').groupby(['sub', 'sup0']).size().rename('N')
smp = k2.groupby(['sub', 'sup0']).size().rename('n')
w = (pop / smp).rename('w').reset_index(); k2 = k2.merge(w, on=['sub', 'sup0'])
j = j.merge(k2[['id', 'w']], on='id')
j = j[~j.id.isin([f'C{i:03d}' for i in range(1, 11)])]          # practice items
print('labelled:', len(j), j.label.value_counts().to_dict())
print('not_a_claim share (extraction error rate, weighted): %.3f' % np.average(j.label == 'not_a_claim', weights=j.w))
r = j[j.label != 'not_a_claim'].copy(); r['y'] = r.label == 'traceable'
def metr(x, col, wt):
    p = x[col]; y = x.y; ww = x.w if wt else np.ones(len(x))
    tp = (ww * (p & y)).sum(); fp = (ww * (p & ~y)).sum(); fn = (ww * (~p & y)).sum(); tn = (ww * (~p & ~y)).sum()
    return dict(precision=tp / (tp + fp) if tp + fp else np.nan, recall=tp / (tp + fn) if tp + fn else np.nan,
                specificity=tn / (tn + fp) if tn + fp else np.nan, acc=(tp + tn) / (tp + fp + fn + tn))
def boot(x, col, wt, B=2000, seed=1):
    rng = np.random.default_rng(seed); subs = x['sub'].unique(); g = {s: x[x['sub'] == s] for s in subs}; out = []
    for _ in range(B):
        xs = pd.concat([g[s] for s in rng.choice(subs, len(subs))]); out.append(metr(xs, col, wt))
    return pd.DataFrame(out).quantile([.025, .975])
for col in ['L1', 'L1nb', 'L2ctx', 'L2']:
    r['p_' + col] = r[col].isin(['supported', 'traced'])
for split in ['all', 'tune', 'test']:
    x = r if split == 'all' else r[r.split == split]
    print(f'\n== {split} (n={len(x)}, traceable={x.y.sum()}) ==')
    for col in ['L1', 'L1nb', 'L2ctx', 'L2']:
        for wt in (False, True):
            m = metr(x, 'p_' + col, wt); ci = boot(x, 'p_' + col, wt, B=500 if split != 'test' else 2000)
            print(f"{col:6s} {'pop' if wt else 'smp'}  " + '  '.join(f"{kk}={m[kk]:.2f}[{ci[kk].iloc[0]:.2f},{ci[kk].iloc[1]:.2f}]" for kk in ['precision', 'recall', 'specificity']))
r.to_csv('data/derived/checker_vs_human.csv', index=False)
