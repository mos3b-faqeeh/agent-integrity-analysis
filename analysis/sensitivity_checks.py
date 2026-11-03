"""Appendix B: sensitivity checks (Table B.1) and processing disposition by agent (Table B.2).
Uses only files in this repository; run analysis/label_distribution.py first.
usage: python analysis/sensitivity_checks.py"""
import glob, json, collections
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.stats import binomtest, wilcoxon

a = pd.read_csv('data/derived/labels_with_weights.csv')
def share(x):
    u = x[x.label.isin(['wrong_source', 'not_found'])]
    return np.average(u.label == 'wrong_source', weights=u.w) if len(u) and u.w.sum() > 0 else np.nan
u = a[a.label.isin(['wrong_source', 'not_found'])]
print(f'wrong-source / unsupported: {int((u.label == "wrong_source").sum())}/{len(u)} = {(u.label == "wrong_source").mean():.4f} raw; '
      f'{share(a):.4f} weighted within selected submissions')

# submission-cluster bootstrap: resample the 17 label-contributing submissions, weights fixed
subs = a['sub'].unique(); g = {s: a[a['sub'] == s] for s in subs}; rng = np.random.default_rng(20261101)
bs = [share(pd.concat([g[k] for k in rng.choice(subs, len(subs), replace=True)])) for _ in range(20000)]
lo, hi = np.nanpercentile(bs, [2.5, 97.5])
print(f'  cluster bootstrap 95% interval ({len(subs)} submissions, 20,000 draws, seed 20261101): {lo:.4f}-{hi:.4f}; '
      f'{u["sub"].nunique()} submissions contain unsupported labels')

# development denominators without the ten practice claims
c = pd.read_csv('labels/claims_to_label.csv'); k = pd.read_csv('labels/claims_to_label_KEY.csv')
pop = pd.read_csv('data/derived/checker_v0_dev_claims.csv')
pop = pop[pop.sig >= 2].assign(sup0=lambda x: x.L2 == 'supported').groupby(['sub', 'sup0']).size().rename('N')
k = k.merge(c[['id', 'sub']], on='id'); k['sup0'] = k.checker_L2 == 'supported'
k = k[~k.id.isin([f'C{i:03d}' for i in range(1, 11)])]
w = (pop / k.groupby(['sub', 'sup0']).size().rename('n')).rename('w').reset_index()
dev = k.merge(w, on=['sub', 'sup0']).merge(pd.read_csv('labels/mosab_labels.csv')[['id', 'label']], on='id')
alt = pd.concat([dev[['sub', 'label', 'w']], a[a['sample'] == 'confirmation'][['sub', 'label', 'w']]])
print(f'  practice claims removed from development denominators: {share(alt):.4f}')

# first annotator's labels before the four rule-based revisions
ag = pd.read_csv('labels/confirm/agreement_A_vs_B.csv'); orig = dict(zip(ag.id, ag.A_orig))
b = a.copy(); b['label'] = [orig[i] if isinstance(orig.get(i), str) else l for i, l in zip(b.id, b.label)]
print(f'  original (pre-revision) confirmation labels: {share(b):.4f}')

# bulk-only matches in the benchmark-wide run
n = m = 0
for f in glob.glob('data/derived/benchmark_run/csv/*.csv'):
    d = pd.read_csv(f); d = d[d.sig >= 2]; n += len(d); m += int(((d.L1 == 'traced') & (d.L1nb != 'traced')).sum())
print(f'bulk-only Level-1 matches: {m}/{n} = {m / n:.4f}')

# judge comparison on the 30 paired submissions
v = pd.read_csv('judge2/vendor_test_by_submission.csv')
print(f'G1 node-failure difference: mean {100 * v.d.mean():.2f} points, Wilcoxon p = {wilcoxon(v.d).pvalue:.4f}')
print(f'G1 gate: exact McNemar p for 7 vs 1 discordant pairs = {binomtest(1, 8, 0.5).pvalue:.4f}')

# fixed-effects regression with clustered errors
s = pd.read_csv('data/derived/submissions.csv'); f = 'R_integrity ~ loghrs + C(model) + C(paper)'
r = smf.ols(f, s).fit(cov_type='HC1'); print(f'log-runtime coefficient {r.params.loghrs:.2f} (HC1 SE {r.bse.loghrs:.2f}, p = {r.pvalues.loghrs:.3f})')
for grp in ['model', 'paper']:
    r = smf.ols(f, s).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(s[grp])[0]})
    print(f'  clustered by {grp}: SE {r.bse.loghrs:.2f}, p = {r.pvalues.loghrs:.3f}')

print('\nTable B.2: processing disposition by agent')
st = {}
for line in open('data/derived/benchmark_run/status.jsonl'):
    r = json.loads(line); st[r['tag']] = r['state']
t = collections.defaultdict(collections.Counter)
for tag, state in st.items(): t[tag.split('__')[0]][state] += 1
print(pd.DataFrame(t).T.fillna(0).astype(int).reindex(columns=['ok', 'no_claims', 'timeout', 'too_big', 'error'], fill_value=0).to_string())
