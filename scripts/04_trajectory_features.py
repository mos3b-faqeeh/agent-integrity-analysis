"""Extract behavioural features from Claude-agent-SDK trajectories (opus-4.8, opus-5, opus-5.5, fable-5)."""
import json, sys, re, glob, os, collections, csv
H = sys.argv[1]; OUT = sys.argv[2]
AGENTS = ['opus-4.8', 'opus-5', 'opus-5.5', 'fable-5']

VERIFY_PAT = re.compile(r'\b(verify|verif|cross-?check|double-?check|sanity|consisten|reconcil|trace|audit|confirm that|matches? the (log|code|paper)|check(ing)? (that|whether|the) )', re.I)
LOG_PAT = re.compile(r'\.(log|json|jsonl|csv|txt|out)\b', re.I)
TEX_PAT = re.compile(r'\.(tex|bib)\b', re.I)
NUM_PAT = re.compile(r'\b\d+\.\d+\b')

def feats(path):
    t = json.load(open(path)); ev = t['events']; m = t['metadata']
    f = collections.Counter()
    f['events'] = len(ev); f['elapsed_h'] = m.get('elapsed_seconds', 0) / 3600; f['attempts'] = m.get('attempts', 1)
    f['completed'] = int(bool(m.get('completed')))
    first_tex_t = None; last_t = 0; think_chars = 0; text_chars = 0
    tool_results_err = 0
    for e in ev:
        x = e['event']; last_t = max(last_t, e['t_offset'])
        if x.get('kind') == 'assistant':
            for c in x.get('content', []):
                ty = c.get('type')
                if ty == 'tool_use':
                    name = c.get('name', '?'); f['tool:' + name] += 1; f['tool_calls'] += 1
                    inp = json.dumps(c.get('input', {}))
                    if name == 'Bash':
                        cmd = c['input'].get('command', '')
                        if re.search(r'\b(python|python3)\b', cmd): f['bash_python'] += 1
                        if re.search(r'\b(cat|head|tail|grep|less|jq)\b', cmd) and LOG_PAT.search(cmd): f['bash_read_log'] += 1
                        if re.search(r'pdflatex|latexmk|xelatex|tectonic', cmd): f['bash_latex'] += 1
                        if re.search(r'\bpytest|unittest|assert\b', cmd): f['bash_test'] += 1
                    if name in ('Read',) and LOG_PAT.search(inp): f['read_log'] += 1
                    if name in ('Edit', 'Write') and TEX_PAT.search(inp):
                        f['write_tex'] += 1
                        if first_tex_t is None: first_tex_t = e['t_offset']
                        if NUM_PAT.search(inp): f['write_tex_with_numbers'] += 1
                    if name in ('Edit', 'Write') and re.search(r'\.py\b', inp): f['write_py'] += 1
                    if name == 'Task': f['subagent'] += 1
                elif ty == 'thinking':
                    s = c.get('thinking', '') or ''; think_chars += len(s)
                    if VERIFY_PAT.search(s): f['verify_mentions_think'] += 1
                elif ty == 'text':
                    s = c.get('text', '') or ''; text_chars += len(s)
                    if VERIFY_PAT.search(s): f['verify_mentions_text'] += 1
        elif x.get('kind') == 'user':
            for c in x.get('content', []) if isinstance(x.get('content'), list) else []:
                if c.get('type') == 'tool_result' and c.get('is_error'): tool_results_err += 1
    f['think_kchars'] = think_chars / 1000; f['text_kchars'] = text_chars / 1000
    f['tool_errors'] = tool_results_err
    f['tex_start_frac'] = (first_tex_t / last_t) if (first_tex_t is not None and last_t) else None
    # actions after first tex write: how much verification/running happens during writing phase
    if first_tex_t is not None:
        post = [e for e in ev if e['t_offset'] >= first_tex_t]
        f['post_tex_bash_python'] = sum(1 for e in post for c in (e['event'].get('content') or []) if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') == 'Bash' and re.search(r'\bpython', c['input'].get('command', '')))
        f['post_tex_read_log'] = sum(1 for e in post for c in (e['event'].get('content') or []) if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') in ('Read', 'Bash') and LOG_PAT.search(json.dumps(c.get('input', {}))))
    return f

rows = []
for a in AGENTS:
    for p in glob.glob(f'{H}/trajectories/{a}/paper*.json'):
        pid = int(re.search(r'paper(\d+)', p).group(1))
        f = feats(p); f['model'] = a; f['paper'] = pid; rows.append(f)
keys = sorted({k for r in rows for k in r}, key=lambda k: (k not in ('model', 'paper'), k))
with open(OUT, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=keys); w.writeheader(); w.writerows(rows)
print(len(rows), 'trajectories ->', OUT)
