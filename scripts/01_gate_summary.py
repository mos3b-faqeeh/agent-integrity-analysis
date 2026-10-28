import json, sys, os, glob, collections, statistics as st
root = sys.argv[1]
idx = json.load(open(os.path.join(root, 'index.json')))
models = {m['dir']: m for m in idx['models']}
papers = {p['id']: p for p in idx['papers']}

# ---------- consensus-level gates ----------
cons = {}
for f in glob.glob(os.path.join(root, '*', 'paper*', 'consensus.json')):
    c = json.load(open(f))
    cons[(c['model'], c['paper'])] = c

print("=== PER-AGENT GATE PASS (consensus, n=15 tasks) ===")
print(f"{'agent':18s} {'G1':>4s} {'G2':>4s} {'G3':>4s} {'all':>4s}  medHrs")
hours = collections.defaultdict(list)
for s in idx['leaderboard']['submissions'] if isinstance(idx['leaderboard'].get('submissions'), list) else []:
    pass
# run hours from index evaluations? check consensus list
for row in idx.get('consensus', []):
    if 'hours' in row: hours[row['model']].append(row['hours'])
for m in models:
    g = collections.Counter()
    for p in papers:
        c = cons[(m, p)]
        for gate in ('G1', 'G2', 'G3'):
            g[gate] += c['gates'][gate]['status'] == 'pass'
        g['all'] += all(c['gates'][x]['status'] == 'pass' for x in ('G1', 'G2', 'G3'))
    h = f"{st.median(hours[m]):.1f}" if hours[m] else "-"
    print(f"{m:18s} {g['G1']:4d} {g['G2']:4d} {g['G3']:4d} {g['all']:4d}  {h}")

print("\n=== PER-TASK G1 PASS (out of 9 agents) ===")
for p in sorted(papers):
    n = sum(cons[(m, p)]['gates']['G1']['status'] == 'pass' for m in models)
    n2 = sum(cons[(m, p)]['gates']['G2']['status'] == 'pass' for m in models)
    print(f"P{p:<3d} grp {papers[p]['group']} {papers[p]['domain']:24s} G1 {n}/9  G2 {n2}/9")

# ---------- integrity node failure frequencies ----------
print("\n=== INTEGRITY NODES: how often each FAILS across 135 submissions (consensus) ===")
nodefail = collections.Counter(); nodeseen = collections.Counter()
for c in cons.values():
    for name, nd in c['nodes'].items():
        if nd.get('gate') == 'G1' and nd.get('role') in ('required', 'conditional', 'composite_member'):
            nodeseen[name] += 1
            if nd['status'] == 'fail': nodefail[name] += 1
for name, k in nodefail.most_common(25):
    print(f"{k:3d}/{nodeseen[name]:3d}  {name}")

# ---------- judge agreement ----------
print("\n=== JUDGE AGREEMENT (fraction of counted nodes with 4/4 unanimous value) ===")
unan = tot = 0; by_gate = collections.defaultdict(lambda: [0, 0])
for c in cons.values():
    for name, nd in c['nodes'].items():
        if nd.get('role') not in ('required', 'conditional', 'composite_member'): continue
        tot += 1; by_gate[nd['gate']][1] += 1
        top = max(v['count'] for v in nd['votes']) if nd.get('votes') else 0
        if top == 4: unan += 1; by_gate[nd['gate']][0] += 1
print(f"overall {unan}/{tot} = {unan/tot:.2%}")
for g, (u, t) in sorted(by_gate.items()): print(f"  {g}: {u}/{t} = {u/t:.2%}")

# gate flip across repeats
print("\n=== GATE INSTABILITY: submissions whose 4 repeats disagree on G1 ===")
rep = collections.defaultdict(list)
for e in idx['evaluations']:
    rep[(e['model'], e['paper'])].append(e['gates']['G1'])
flip = sum(1 for v in rep.values() if len(set(v)) > 1)
print(f"{flip}/{len(rep)} submissions have mixed G1 verdicts across repeats")
oc = collections.Counter(e['outcome'] for e in idx['evaluations'])
print("outcome labels over 540 judgments:", dict(oc))
