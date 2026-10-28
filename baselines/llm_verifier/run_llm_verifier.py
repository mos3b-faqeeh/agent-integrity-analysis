"""LLM-verifier baseline: ask an LLM (via the `claude` CLI, logged in) to label each of the 211 labelled real claims,
given exactly the information the human annotators saw (guide, paper context, top-3 matching entries). Blind to the
human labels and the checker. Resumable: already-answered ids in results.jsonl are skipped.

usage (from the repo root, on a machine with the claude CLI logged in):
    python3 baselines/llm_verifier/run_llm_verifier.py [--model MODEL] [--limit N]
Each call runs in an empty temporary directory with a single turn, so the model cannot read any files.
"""
import argparse, json, os, subprocess, tempfile, time, re
ap = argparse.ArgumentParser(); ap.add_argument('--model', default=None); ap.add_argument('--limit', type=int, default=0)
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
P, R = os.path.join(HERE, 'prompts.jsonl'), os.path.join(HERE, 'results.jsonl')
done = set()
if os.path.exists(R):
    for line in open(R):
        try: done.add(json.loads(line)['id'])
        except Exception: pass
todo = [json.loads(l) for l in open(P) if json.loads(l)['id'] not in done]
if a.limit: todo = todo[:a.limit]
print(f'{len(done)} done, {len(todo)} to do', flush=True)
LABELS = ['TRACEABLE', 'WRONG_SOURCE', 'NOT_FOUND', 'NOT_A_CLAIM']
with tempfile.TemporaryDirectory() as empty:
    for i, x in enumerate(todo, 1):
        cmd = ['claude', '-p', x['prompt'], '--output-format', 'json', '--max-turns', '1']
        if a.model: cmd += ['--model', a.model]
        for attempt in range(3):
            try:
                out = subprocess.run(cmd, cwd=empty, capture_output=True, text=True, timeout=300)
                j = json.loads(out.stdout); text = j.get('result', '') or ''
                break
            except Exception as e:
                text, j = f'ERROR {e}', {}; time.sleep(20)
        m = re.search(r'\b(' + '|'.join(LABELS) + r')\b', text.upper())
        rec = dict(id=x['id'], set=x['set'], label=m.group(1) if m else 'UNPARSED', raw=text[:500],
                   model=a.model or j.get('model') or 'cli-default', usage=j.get('modelUsage') or j.get('usage'))
        with open(R, 'a') as f: f.write(json.dumps(rec) + '\n')
        print(f'[{i}/{len(todo)}] {x["id"]} -> {rec["label"]}', flush=True)
print('done')
