"""Agreement between the official GPT-6-Astra judge and a second judge (e.g. Claude-Opus-5.5) on the
stratified sample. Both judge trees must have the layout artifacts/judge_results/<judge>/<agent>/paper<i>/
(consensus.json or repeat_XX/grade.json) as produced by the benchmark's graders.

usage: python scripts/05_judge_agreement.py <astra_root> <second_root> judge2/stratified_sample.csv
"""
import json, os, sys, collections, itertools
import pandas as pd, numpy as np

A, B, SAMPLE = sys.argv[1], sys.argv[2], sys.argv[3]
VENDOR = {'astra-6': 'openai', 'sol-5.6': 'openai', 'opus-4.8': 'anthropic', 'opus-5': 'anthropic',
          'opus-5.5': 'anthropic', 'fable-5': 'anthropic', 'kimi-k3': 'open', 'deepseek-v4-pro': 'open', 'glm-5.3': 'open'}
COUNTED = ('required', 'conditional', 'composite_member')


def load(root, model, paper):
    """Return {node: status} and gates for a submission; prefer consensus.json, else majority over repeats."""
    d = os.path.join(root, model, f'paper{paper}')
    cp = os.path.join(d, 'consensus.json')
    if os.path.exists(cp):
        c = json.load(open(cp))
        nodes = {k: v['status'] for k, v in c['nodes'].items() if v.get('role') in COUNTED}
        gates = {g: c['gates'][g]['status'] for g in ('G1', 'G2', 'G3')}
        return nodes, gates
    reps = sorted(p for p in os.listdir(d) if p.startswith('repeat_'))
    votes = collections.defaultdict(collections.Counter); gvotes = collections.defaultdict(collections.Counter)
    for r in reps:
        g = json.load(open(os.path.join(d, r, 'grade.json')))
        for k, v in g['nodes'].items():
            if v.get('role') in COUNTED: votes[k][v['status']] += 1
        for gg in ('G1', 'G2', 'G3'): gvotes[gg][g['gates'][gg]['status'] if isinstance(g['gates'][gg], dict) else g['gates'][gg]] += 1
    maj = lambda c: c.most_common(1)[0][0] if c and c.most_common(1)[0][1] > sum(c.values()) / 2 else 'fail'
    return {k: maj(c) for k, c in votes.items()}, {g: maj(c) for g, c in gvotes.items()}


def kappa(a, b):
    a, b = np.array(a), np.array(b); po = (a == b).mean()
    cats = set(a) | set(b); pe = sum((a == c).mean() * (b == c).mean() for c in cats)
    return (po - pe) / (1 - pe) if pe < 1 else float('nan')


sample = pd.read_csv(SAMPLE)
rows, node_rows = [], []
for m, p in sample[['model', 'paper']].values:
    try:
        na, ga = load(A, m, int(p)); nb, gb = load(B, m, int(p))
    except FileNotFoundError:
        print(f'skip {m}/paper{p}: missing in one judge tree'); continue
    common = sorted(set(na) & set(nb))
    for k in common:
        node_rows.append(dict(model=m, paper=p, vendor=VENDOR[m], node=k, gate=k.split(':')[0], a=na[k], b=nb[k]))
    rows.append(dict(model=m, paper=p, vendor=VENDOR[m], n_nodes=len(common),
                     agree=np.mean([na[k] == nb[k] for k in common]) if common else np.nan,
                     G1_a=ga['G1'], G1_b=gb['G1'], G2_a=ga['G2'], G2_b=gb['G2'], G3_a=ga['G3'], G3_b=gb['G3']))
sub = pd.DataFrame(rows); nd = pd.DataFrame(node_rows)
if nd.empty: sys.exit('no overlapping judgments found')

print(f'=== {len(sub)} submissions, {len(nd)} shared counted nodes ===')
print(f'node-level agreement: {(nd.a == nd.b).mean():.1%}   kappa={kappa(nd.a, nd.b):.3f}')
g1 = nd[nd.node.str.startswith('integrity')]
print(f'G1 nodes only:        {(g1.a == g1.b).mean():.1%}   kappa={kappa(g1.a, g1.b):.3f}')
for gate in ('G1', 'G2', 'G3'):
    print(f'{gate} gate agreement: {(sub[gate + "_a"] == sub[gate + "_b"]).mean():.1%}')

print('\n=== G1-node agreement and second-judge leniency by agent vendor ===')
g1 = g1.assign(agree=(g1.a == g1.b), b_fail=(g1.b == 'fail'), a_fail=(g1.a == 'fail'))
t = g1.groupby('vendor').agg(n=('agree', 'size'), agree=('agree', 'mean'), astra_fail=('a_fail', 'mean'), second_fail=('b_fail', 'mean'))
t['second_minus_astra'] = t.second_fail - t.astra_fail
print(t.round(3).to_string())
print('\nInterpretation: a vendor interaction shows as second_minus_astra differing in sign/size across vendors '
      '(e.g. negative for openai, positive elsewhere => Astra was lenient to OpenAI agents).')

print('\n=== per-agent ===')
print(g1.groupby('model').agg(n=('agree', 'size'), agree=('agree', 'mean'), astra_fail=('a_fail', 'mean'), second_fail=('b_fail', 'mean')).round(3).to_string())

dis = nd[nd.a != nd.b]
dis.to_csv('judge2/disagreements.csv', index=False)
sub.to_csv('judge2/agreement_by_submission.csv', index=False)
print(f'\n{len(dis)} disagreeing nodes written to judge2/disagreements.csv for human adjudication')
