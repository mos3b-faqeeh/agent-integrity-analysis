"""Final evaluation of the frozen operating points on the fresh confirmation sample.
Reference: Mosab's labels (72 claims); also annotator B (48) and A=B consensus. Population weights = N_stratum/n_stratum.
usage: python analysis/score_confirm.py <scratch_dir_with_ccc_and_confirm_ordered_all.csv>"""
import sys, json, glob, os, numpy as np, pandas as pd
S = sys.argv[1]
sheet = pd.read_csv(f'{S}/confirm_ordered_all.csv', dtype={'claim': str})
cc = pd.concat([pd.read_csv(f, dtype={'raw': str}).assign(sub=os.path.basename(f)[:-4]) for f in glob.glob(f'{S}/ccc/*.csv') if 'fast' not in f])
cc = cc[cc.sig >= 2]; cc['ctx'] = cc.context.astype(str).str[:500]
sheet['ctx'] = sheet.paper_context.astype(str)
# the sheet stored claims through a float round-trip ('1.00' -> '1.0'), so match on context and numeric value
d = sheet.merge(cc, on=['sub', 'ctx'], how='left', suffixes=('', '_cc'))
num = lambda v: pd.to_numeric(pd.Series(v).astype(str).str.replace(r'[^0-9eE.+-]', '', regex=True), errors='coerce')
d = d[np.isclose(num(d.claim).values, num(d.raw).values, rtol=1e-9, atol=0) | (d.claim.astype(str) == d.raw.astype(str))].drop_duplicates('id')
assert len(d) == len(sheet), set(sheet.id) - set(d.id)
assert d.v1_s.notna().all(), d[d.v1_s.isna()].id.tolist()
d['w'] = d.N_stratum / d.n_stratum
A = pd.read_csv('labels/confirm/mosab_confirm_labels.csv')[['id', 'label']].rename(columns={'label': 'A'})
B = pd.read_csv('labels/confirm/annotatorB_labels.csv')[['id', 'label']].rename(columns={'label': 'B'})
d = d.merge(A, on='id').merge(B, on='id', how='left')
op = json.load(open('checker/operating_points.json'))
def metr(x, ref, o, wt=True):
    x = x[x[ref].notna() & (x[ref] != 'not_a_claim')]; y = x[ref] == 'traceable'
    ok = (x.v1_s >= o['tau']) & (x.v1_p <= o['pmax']) & (x.v1_s > 0); w = x.w if wt else 1
    tp = (w * (ok & y)).sum(); fp = (w * (ok & ~y)).sum(); fn = (w * (~ok & y)).sum()
    return (tp / (tp + fp) if tp + fp else np.nan), (tp / (tp + fn) if tp + fn else np.nan), len(x), int(y.sum())
def boot(x, ref, o, B=2000):
    rng = np.random.default_rng(7); subs = x['sub'].unique(); g = {s: x[x['sub'] == s] for s in subs}
    bs = np.array([metr(pd.concat([g[s] for s in rng.choice(subs, len(subs))]), ref, o)[:2] for _ in range(B)], float)
    return np.nanpercentile(bs, 2.5, axis=0), np.nanpercentile(bs, 97.5, axis=0)
d['AB'] = np.where(d.B.notna() & (d.A == d.B), d.A, None)
out = []
for ref in ['A', 'B', 'AB']:
    for name in ['strict', 'balanced', 'broad']:
        o = op[name]; p, r, n, npos = metr(d, ref, o); lo, hi = boot(d, ref, o)
        out.append(dict(reference=ref, setting=name, n=n, n_traceable=npos, precision=p, p_lo=lo[0], p_hi=hi[0], recall=r, r_lo=lo[1], r_hi=hi[1]))
        l1 = None
res = pd.DataFrame(out).round(3); print(res.to_string(index=False))
# naive baseline (L1: value appears anywhere) against A
x = d[d.A != 'not_a_claim']; y = x.A == 'traceable'; ok = x.L1 == 'traced'
print('L1 vs A: precision %.3f recall %.3f specificity %.3f' % (np.average(y[ok], weights=x.w[ok]), np.average(ok[y], weights=x.w[y]), np.average(~ok[~y], weights=x.w[~y])))
print('not_a_claim share (A, weighted): %.3f' % np.average(d.A == 'not_a_claim', weights=d.w))
res.to_csv('data/derived/confirmation_results.csv', index=False)
d.drop(columns=['ctx']).to_csv('data/derived/confirmation_checker_vs_human.csv', index=False)
