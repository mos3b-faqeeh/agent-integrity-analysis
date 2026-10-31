"""Tables 7 (precision with counts), 8 (component ablation) and 9 (baselines) from the per-claim file
data/derived/baselines_scored.csv plus the checker's Level-1 flags.
Precision intervals: Clopper-Pearson 95% on unweighted counts.
usage: python analysis/tables_precision_ablation_baselines.py"""
import glob, os, numpy as np, pandas as pd
from scipy.stats import beta

def cp(k, n):
    lo = beta.ppf(0.025, k, n - k + 1) if k else 0.0; hi = beta.ppf(0.975, k + 1, n - k) if k < n else 1.0
    return lo, hi
def row(name, m, y, w=None):
    k, n = int((m & y).sum()), int(m.sum()); lo, hi = cp(k, n)
    rec = (m & y).sum() / y.sum(); wrec = (w * (m & y)).sum() / (w * y).sum() if w is not None else np.nan
    print(f'{name:38s} certified {n:4d}  traceable {k:4d}  precision {k/n:.2f} [{lo:.2f}, {hi:.2f}]  recall {rec:.2f} ({wrec:.2f})')

d = pd.read_csv('data/derived/baselines_scored.csv'); y = d.y.astype(bool)
# Level-1 flags: development claims from the scored dev file, confirmation claims from the confirmation run
dev = pd.read_csv('data/derived/checker_vs_human.csv')[['id', 'L1', 'L1nb']]
sheet = pd.read_csv('data/derived/confirmation_run/confirm_ordered_all.csv', dtype={'claim': str})
cc = pd.concat([pd.read_csv(f, dtype={'raw': str}).assign(sub=os.path.basename(f)[:-4])
                for f in glob.glob('data/derived/confirmation_run/ccc/*.csv')])
cc = cc[cc.sig >= 2]; cc['ctx'] = cc.context.astype(str).str[:500]; sheet['ctx'] = sheet.paper_context.astype(str)
num = lambda v: pd.to_numeric(pd.Series(v).astype(str).str.replace(r'[^0-9eE.+-]', '', regex=True), errors='coerce')
j = sheet.merge(cc, on=['sub', 'ctx'], how='left', suffixes=('', '_cc'))
j = j[np.isclose(num(j.claim).values, num(j.raw).values, rtol=1e-9, atol=0) | (j.claim.astype(str) == j.raw.astype(str))]
conf = j.drop_duplicates('id')[['id', 'L1', 'L1nb']]
d = d.merge(pd.concat([dev, conf]), on='id', how='left'); assert d.L1.notna().all()
L1 = d.L1 == 'traced'; L1nb = d.L1nb == 'traced'
score = (d.v1_s >= 0.12) & (d.v1_s > 0); decoy = (d.v1_p <= 0.1) & (d.v1_s > 0); strict = d.strict.astype(bool)

print('Table 7: strict checker precision')
for nm, s in [('development', d.set == 'dev'), ('confirmation', d.set == 'conf'), ('pooled', d.set.notna())]:
    k, n = int((strict & y & s).sum()), int((strict & s).sum()); lo, hi = cp(k, n)
    print(f'  {nm:13s} real {int(s.sum()):3d}  certified {n:3d}  traceable {k:3d}  {k/n:.2f} [{lo:.2f}, {hi:.2f}]')

print('\nTable 8: ablation on all labelled real claims')
for nm, m in [('Level 1', L1), ('+ ignore bulk data', L1nb), ('+ context score (no decoys)', L1nb & score),
              ('decoy test only', L1nb & decoy), ('full strict', strict)]:
    row(nm, m, y, d.w)
dv = pd.read_csv('data/derived/checker_v1_dev_claims.csv'); dv = dv[dv.sig >= 2]
sc = pd.read_csv('data/derived/checker_v1_dev_claims_scorers.csv'); sc = sc[sc.sig >= 2]
print(f'decoy acceptance over the {len(dv)} development claims with >= 2 significant digits (offset +7 decoy):')
for nm, v in [('Level 1', dv.decoy_L1.mean()), ('+ ignore bulk data', dv.decoy_L1nb.mean()),
              ('+ context score', ((sc.v1_dec_s >= 0.12) & (sc.v1_dec_s > 0)).mean()),
              ('decoy test only', ((sc.v1_dec_p <= 0.1) & (sc.v1_dec_s > 0)).mean()),
              ('full strict', ((sc.v1_dec_p <= 0.1) & (sc.v1_dec_s >= 0.12)).mean())]:
    print(f'  {nm:28s} {100 * v:.1f}%')

print('\nTable 9: baselines on the claims not used for tuning (development test split + confirmation)')
# embedding thresholds were tuned on the development tuning split to match the strict checker's precision there (0.96):
# tau = 0.45 for the score alone and tau = 0.28 together with the decoy test (p <= 0.1)
EMB_TAU, EMB_DEC_TAU = 0.45, 0.28
t = d[d.split == 'tune']
for nm, m in [('strict', t.strict.astype(bool)), ('embedding score', t.emb_s >= EMB_TAU),
              ('embedding + decoy', (t.emb_p <= 0.1) & (t.emb_s >= EMB_DEC_TAU) & (t.emb_s > 0))]:
    print(f'  tuning-split precision, {nm:18s} {(m & t.y.astype(bool)).sum() / m.sum():.3f}  (n = {int(m.sum())})')
h = d.split.isin(['test', 'conf']); x = d[h]; yy = y[h]
for nm, m in [('Level 1', L1[h]), ('embedding score', x.emb_s >= EMB_TAU),
              ('embedding + decoy', (x.emb_p <= 0.1) & (x.emb_s >= EMB_DEC_TAU) & (x.emb_s > 0)),
              ('LLM verifier', x.llm.astype(bool)), ('checker AND LLM', strict[h] & x.llm.astype(bool)), ('strict checker', strict[h])]:
    row(nm, m, yy)
