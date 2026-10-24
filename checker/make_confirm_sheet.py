"""Fresh confirmation sample (2026-10-24): unused submissions, one per agent, sampled independently per submission.
Stratified like the dev sheet (~40% strict-supported) with a per-submission seed, so submissions can be added as
their checker runs finish without changing earlier draws. IDs N<sub-index><nn>; shuffled order within a submission.
usage: python checker/make_confirm_sheet.py <checker_csv> <sub_dir> <out_csv> [--n 9]"""
import sys, argparse, hashlib, random
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import claimcheck as cc
ap = argparse.ArgumentParser(); ap.add_argument('claims'); ap.add_argument('sub'); ap.add_argument('out'); ap.add_argument('--n', type=int, default=9)
a = ap.parse_args(); sub = Path(a.sub).name
seed = int(hashlib.sha256(f'confirm-20261024-{sub}'.encode()).hexdigest()[:8], 16); rng = random.Random(seed)
g = pd.read_csv(a.claims); g = g[g.sig >= 2]
sup = g[g.L2 == 'supported']; uns = g[g.L2 != 'supported']
k_sup = min(len(sup), round(a.n * 0.4)); k_uns = min(len(uns), a.n - k_sup)
pick = pd.concat([sup.sample(k_sup, random_state=rng.randrange(10**9)), uns.sample(k_uns, random_state=rng.randrange(10**9))])
pick = pick.sample(frac=1, random_state=rng.randrange(10**9))
ev = cc.evidence_index(Path(a.sub)); lk = cc.build_lookup(ev); rows = []
for _, c in pick.iterrows():
    claim = dict(value=c.value, dec=int(c.dec), context=c.context, pct=str(c.pct) == 'True')
    m = cc.matches(claim, ev, lk)
    cand = sorted(((ev[i][4], -cc.provenance_score(claim, ev[i]), i) for i in m))[:3]
    r = dict(sub=sub, agent=sub.split('__')[0], paper=sub.split('__paper')[1], kind=c.kind, claim=c.raw, paper_context=str(c.context)[:500],
             N_stratum=len(sup) if c.L2 == 'supported' else len(uns), n_stratum=k_sup if c.L2 == 'supported' else k_uns, checker_L2=c.L2)
    for j in range(3):
        if j < len(cand):
            _, negs, i = cand[j]; v, ctx, f, _, bulk = ev[i]
            r.update({f'cand{j+1}_file': f, f'cand{j+1}_context': str(ctx)[:250], f'cand{j+1}_value': v, f'cand{j+1}_bulk': bulk})
        else:
            r.update({f'cand{j+1}_file': '', f'cand{j+1}_context': '', f'cand{j+1}_value': '', f'cand{j+1}_bulk': ''})
    r['n_candidates_total'] = len(m); rows.append(r)
pd.DataFrame(rows).to_csv(a.out, index=False); print(sub, len(rows), 'claims', k_sup, 'supported-stratum')
