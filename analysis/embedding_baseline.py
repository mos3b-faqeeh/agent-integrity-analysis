"""Embedding-similarity baseline: same candidate matching (Level 1, non-bulk) and decoy calibration as the checker,
but the provenance score is cosine similarity between sentence embeddings (all-MiniLM-L6-v2) of the claim context and
of the evidence entry context + file path. Scored on the 211 labelled real claims. Matches capped at 300 per value.
usage: python analysis/embedding_baseline.py <dev_dir> <conf_dir> <out_csv>"""
import sys, numpy as np, pandas as pd
from pathlib import Path
sys.path.insert(0, 'checker'); import claimcheck as cc
from sentence_transformers import SentenceTransformer
DEV, CONF, OUT = sys.argv[1:4]
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu')
d = pd.read_csv('data/derived/checker_vs_human.csv'); d = d[d.label != 'not_a_claim'].assign(set='dev', y=lambda x: x.label == 'traceable')
c = pd.read_csv('data/derived/confirmation_checker_vs_human.csv'); c = c[c.A != 'not_a_claim'].assign(set='conf', y=lambda x: x.A == 'traceable', split='conf')
cols = ['id', 'sub', 'value', 'dec', 'pct', 'context', 'y', 'w', 'set', 'split']
X = pd.concat([d[cols], c[cols]], ignore_index=True)
cache = {}
def emb(texts):
    new = [t for t in set(texts) if t not in cache]
    if new:
        for t, v in zip(new, model.encode(new, batch_size=256, normalize_embeddings=True, show_progress_bar=False)): cache[t] = v
    return np.array([cache[t] for t in texts])
def best(claim, rows, lk, cvec):
    m = [i for i in cc.matches(claim, rows, lk) if not rows[i][4]]
    if not m: return 0.0
    if len(m) > 300: m = m[:: len(m) // 300 + 1]
    E = emb([(rows[i][1] + ' ' + rows[i][3])[:300] for i in m])
    return float((E @ cvec).max())
out = []
for sub, g in X.groupby('sub'):
    sd = Path(DEV if g.set.iloc[0] == 'dev' else CONF) / sub
    rows = cc.evidence_index(sd); lk = cc.build_lookup(rows)
    for _, r in g.iterrows():
        claim = dict(value=r.value, dec=int(r.dec), context=str(r.context), pct=str(r.pct) == 'True')
        cvec = emb([str(r.context)[:400]])[0]
        s = best(claim, rows, lk, cvec)
        dec = [best(cc._at(claim, cc._shift(claim, k)), rows, lk, cvec) for k in cc.CAL_OFFSETS if cc._shift(claim, k) * claim['value'] > 0]
        p = (1 + sum(x >= s for x in dec)) / (1 + len(dec)) if s > 0 else 1.0
        dk = cc._at(claim, cc._shift(claim, cc.TEST_OFFSET)); ds = best(dk, rows, lk, cvec)
        ddec = [best(cc._at(dk, cc._shift(dk, k)), rows, lk, cvec) for k in cc.CAL_OFFSETS if cc._shift(dk, k) * dk['value'] > 0]
        dp = (1 + sum(x >= ds for x in ddec)) / (1 + len(ddec)) if ds > 0 else 1.0
        out.append(dict(id=r.id, sub=sub, set=r.set, split=r.split, y=r.y, w=r.w, emb_s=s, emb_p=p, emb_dec_s=ds, emb_dec_p=dp))
    print(sub, len(g), flush=True)
pd.DataFrame(out).to_csv(OUT, index=False)
