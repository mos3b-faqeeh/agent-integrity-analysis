"""Build the human labelling sheet for claimcheck validation.

Stratified sample of numeric claims (per submission x checker verdict), each with its paper context and the
top-3 candidate evidence entries (non-bulk first) so the annotator can decide:
    traceable          -- one of the candidates (or another artifact) is the value the claim reports
    wrong_source       -- the number appears, but only from a different experiment/metric/run
    not_found          -- no artifact supports the value
    not_a_claim        -- extraction error (citation, index, formatting, etc.)
Half the rows are marked split=tune (rules may be adjusted on them), half split=test (held out).

usage: python checker/make_label_sheet.py <claims_csv> <dev_dir> <out_csv> [--per-sub 22] [--seed 20261023]
"""
import sys, argparse, random
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).parent))
import claimcheck as cc

ap = argparse.ArgumentParser(); ap.add_argument('claims'); ap.add_argument('dev'); ap.add_argument('out')
ap.add_argument('--per-sub', type=int, default=22); ap.add_argument('--seed', type=int, default=20261023)
a = ap.parse_args(); rng = random.Random(a.seed)
df = pd.read_csv(a.claims)
df = df[df.sig >= 2]                     # 1-significant-digit claims are mechanically unverifiable (reported separately)
rows = []
for sub, g in df.groupby('sub'):
    sup = g[g.L2 == 'supported']; uns = g[g.L2 != 'supported']
    k_sup = min(len(sup), round(a.per_sub * 0.4)); k_uns = min(len(uns), a.per_sub - k_sup)
    pick = pd.concat([sup.sample(k_sup, random_state=rng.randrange(10**9)), uns.sample(k_uns, random_state=rng.randrange(10**9))])
    sd = Path(a.dev) / sub
    ev = cc.evidence_index(sd); lk = cc.build_lookup(ev)
    for _, c in pick.iterrows():
        claim = dict(value=c.value, dec=int(c.dec), context=c.context, pct=str(c.pct) == 'True')
        m = cc.matches(claim, ev, lk)
        cand = sorted(((ev[i][4], -cc.provenance_score(claim, ev[i]), i) for i in m))[:3]   # non-bulk first, then score
        r = dict(sub=sub, agent=sub.split('__')[0], paper=sub.split('__paper')[1], kind=c.kind, claim=c.raw,
                 paper_context=str(c.context)[:500], checker_L2=c.L2, checker_score=c.L2_score)
        for j in range(3):
            if j < len(cand):
                _, negs, i = cand[j]; v, ctx, f, _, bulk = ev[i]
                r[f'cand{j+1}_file'] = f; r[f'cand{j+1}_context'] = str(ctx)[:250]; r[f'cand{j+1}_value'] = v
                r[f'cand{j+1}_bulk'] = bulk; r[f'cand{j+1}_score'] = round(-negs, 3)
            else:
                r[f'cand{j+1}_file'] = r[f'cand{j+1}_context'] = r[f'cand{j+1}_value'] = ''; r[f'cand{j+1}_bulk'] = ''; r[f'cand{j+1}_score'] = ''
        r['n_candidates_total'] = len(m)
        rows.append(r)
out = pd.DataFrame(rows).sample(frac=1, random_state=a.seed).reset_index(drop=True)   # shuffle so verdicts are not grouped
out.insert(0, 'id', [f'C{i+1:03d}' for i in range(len(out))])
out['split'] = ['tune' if i % 2 == 0 else 'test' for i in range(len(out))]
out['LABEL'] = ''; out['correct_file_if_other'] = ''; out['notes'] = ''
# annotator should not be anchored by the checker's verdict: keep it in a separate key file
key = out[['id', 'checker_L2', 'checker_score', 'split']]
out.drop(columns=['checker_L2', 'checker_score']).to_csv(a.out, index=False)
key.to_csv(a.out.replace('.csv', '_KEY.csv'), index=False)
print(len(out), 'claims ->', a.out, '| key ->', a.out.replace('.csv', '_KEY.csv'))
print(out.groupby('agent').size().to_dict())
