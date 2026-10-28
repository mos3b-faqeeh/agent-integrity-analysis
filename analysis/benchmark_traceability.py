"""Benchmark-wide traceability from the frozen strict checker, per submission and per agent,
and its relation to the official judge's integrity verdicts.

Corrected traceable share  T = S * precision / recall, where S is the share of a submission's numeric claims
(>= 2 significant digits) that the strict checker certifies, and precision/recall come from the fresh
confirmation sample (human reference). T is a rough, model-based estimate (clipped at 1); S is the
conservative, assumption-free lower bound and is the primary quantity.
usage: python analysis/benchmark_traceability.py <run_dir>     (run_dir from analysis/run_checker_all.py)
"""
import sys, json, glob, os
import numpy as np, pandas as pd
from scipy.stats import spearmanr

R = sys.argv[1]
conf = pd.read_csv('data/derived/confirmation_results.csv')
c = conf[(conf.reference == 'A') & (conf.setting == 'strict')].iloc[0]
PREC, REC = c.precision, c.recall
rows = []
for f in glob.glob(f'{R}/csv/*.csv'):
    tag = os.path.basename(f)[:-4]; m, p = tag.split('__paper')
    d = pd.read_csv(f); d = d[d.sig >= 2]
    if not len(d): continue
    rows.append(dict(model=m, paper=int(p), n_claims=len(d), S=(d.L2 == 'supported').mean(),
                     L1=(d.L1 == 'traced').mean(), untraced=(d.L1 == 'untraced').mean()))
sub = pd.DataFrame(rows)
sub['T_est'] = (sub.S * PREC / REC).clip(upper=1)
st = [json.loads(l) for l in open(f'{R}/status.jsonl')]
last = {r['tag']: r for r in st}
cover = pd.Series({k: v['state'] for k, v in last.items()}).value_counts().to_dict()

js = pd.read_csv('data/derived/submissions.csv')[['model', 'paper', 'R_integrity', 'G1']]
nodes = pd.read_csv('data/derived/integrity_nodes.csv')
nt = nodes[nodes.node.str.contains('number_traceability')].assign(fail=lambda x: x.status == 'fail')
nt = nt.groupby(['model', 'paper']).fail.mean().rename('judge_numtrace_fail').reset_index()
sub = sub.merge(js, on=['model', 'paper'], how='left').merge(nt, on=['model', 'paper'], how='left')

print(f'coverage: {len(sub)} submissions with claims; status counts {cover}')
print(f'correction uses precision {PREC:.2f}, recall {REC:.2f} (strict, fresh sample, annotator A)\n')
ag = sub.groupby('model').agg(n=('paper', 'size'), claims=('n_claims', 'sum'), S_median=('S', 'median'),
                              S_mean=('S', 'mean'), T_est_mean=('T_est', 'mean'), R_integrity=('R_integrity', 'mean'),
                              G1_pass=('G1', 'sum')).sort_values('S_mean', ascending=False)
print(ag.round(3).to_string())
ok = sub.dropna(subset=['R_integrity'])
r1 = spearmanr(ok.S, ok.R_integrity); print(f'\nSpearman(S, judge R_integrity) = {r1.statistic:.2f}, p = {r1.pvalue:.3g}, n = {len(ok)}')
ok2 = sub.dropna(subset=['judge_numtrace_fail'])
r2 = spearmanr(ok2.S, ok2.judge_numtrace_fail); print(f'Spearman(S, judge number-traceability fail rate) = {r2.statistic:.2f}, p = {r2.pvalue:.3g}, n = {len(ok2)}')
# agent-level: does checker ranking match judge ranking?
r3 = spearmanr(ag.S_mean, ag.R_integrity); print(f'agent-level Spearman(S_mean, R_integrity) = {r3.statistic:.2f}, p = {r3.pvalue:.3g}, n = {len(ag)}')
sub.to_csv('data/derived/benchmark_traceability_by_submission.csv', index=False)
ag.to_csv('data/derived/benchmark_traceability_by_agent.csv')
