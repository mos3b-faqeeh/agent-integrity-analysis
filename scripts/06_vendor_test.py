"""Formal test for judge-vendor interaction on G1 (integrity) nodes, second judge vs official judge.
Unit of inference = submission (30). For each submission: d = second-judge G1 fail rate - official G1 fail rate
(majority labels, nodes both judges graded). Tests: (1) is the second judge more lenient overall (Wilcoxon on d);
(2) does d differ by agent vendor (Kruskal-Wallis; permutation test of anthropic vs non-anthropic mean d);
(3) node-level logistic GEE: fail ~ judge * vendor, clustered by submission.
usage: python scripts/06_vendor_test.py <astra_root> <second_root> <sample_csv>"""
import sys, numpy as np, pandas as pd
from scipy.stats import wilcoxon, kruskal
sys.argv, args = sys.argv[:1] + sys.argv[1:4], sys.argv[1:4]
src = open('scripts/05_judge_agreement.py').read(); ns = {'__name__': 'x', 'sys': sys}
exec(src[:src.index('def load_repeats')], ns)
load, VENDOR = ns['load'], ns['VENDOR']
A, B, S = args
smp = pd.read_csv(S); rows, long = [], []
for m, p in smp[['model', 'paper']].values:
    na, _ = load(A, m, p); nb, _ = load(B, m, p)
    ks = [k for k in set(na) & set(nb) if k.startswith('integrity')]
    if not ks: continue
    fa = np.mean([na[k] == 'fail' for k in ks]); fb = np.mean([nb[k] == 'fail' for k in ks])
    rows.append(dict(model=m, paper=p, vendor=VENDOR[m], n=len(ks), gpt_fail=fa, second_fail=fb, d=fb - fa))
    for k in ks:
        long += [dict(sub=f'{m}/{p}', vendor=VENDOR[m], judge=0, fail=int(na[k] == 'fail')),
                 dict(sub=f'{m}/{p}', vendor=VENDOR[m], judge=1, fail=int(nb[k] == 'fail'))]
d = pd.DataFrame(rows); print(d.groupby('vendor')[['gpt_fail', 'second_fail', 'd']].agg(['mean', 'count']).round(3))
w = wilcoxon(d.d); print(f'\n(1) second judge more lenient overall: mean d = {d.d.mean():.3f}, Wilcoxon p = {w.pvalue:.3g}, n = {len(d)}')
k = kruskal(*[g.d for _, g in d.groupby('vendor')]); print(f'(2) d differs by vendor: Kruskal-Wallis p = {k.pvalue:.3g}')
rng = np.random.default_rng(0); isA = (d.vendor == 'anthropic').values; obs = d.d[isA].mean() - d.d[~isA].mean()
perm = [(lambda s: d.d.values[s].mean() - d.d.values[~s].mean())(rng.permutation(isA)) for _ in range(20000)]
print(f'    anthropic minus others mean d = {obs:.3f}, two-sided permutation p = {np.mean(np.abs(perm) >= abs(obs)):.3g}')
isO = (d.vendor == 'openai').values; obs2 = d.d[isO].mean() - d.d[~isO].mean()
perm2 = [(lambda s: d.d.values[s].mean() - d.d.values[~s].mean())(rng.permutation(isO)) for _ in range(20000)]
print(f'    openai minus others mean d = {obs2:.3f}, two-sided permutation p = {np.mean(np.abs(perm2) >= abs(obs2)):.3g}')
try:
    import statsmodels.formula.api as smf, statsmodels.api as sm
    L = pd.DataFrame(long)
    g = smf.gee('fail ~ judge * C(vendor, Treatment("open"))', 'sub', L, family=sm.families.Binomial(), cov_struct=sm.cov_struct.Exchangeable()).fit()
    print('\n(3) node-level GEE (logit), reference vendor = open-weight:'); print(g.summary().tables[1])
except Exception as e:
    print('GEE skipped:', e)
d.to_csv('judge2/vendor_test_by_submission.csv', index=False)
