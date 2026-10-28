"""Run the frozen claim checker over every benchmark submission (smallest first), resumably.

One downloader fetches a submission's file system from Hugging Face, extracts only what the checker reads
(paper source + result-file types), and deletes the archive; two workers run checker/claimcheck.py with a
per-submission timeout. Outputs: <out>/csv/<agent>__paper<N>.csv, and one JSON line per submission in <out>/status.jsonl.
usage: python analysis/run_checker_all.py <out_dir> [--max-gb 10] [--timeout 2400] [--workers 2]
"""
import argparse, json, os, queue, shutil, subprocess, sys, threading, time, glob
from pathlib import Path
import pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument('out'); ap.add_argument('--max-gb', type=float, default=10)
ap.add_argument('--timeout', type=int, default=2400); ap.add_argument('--workers', type=int, default=2)
a = ap.parse_args(); OUT = Path(a.out); (OUT / 'csv').mkdir(parents=True, exist_ok=True)
CHECK = Path(__file__).resolve().parent.parent / 'checker' / 'claimcheck.py'
KEEP = ['*.tex', '*.bbl', '*.pdf', '*.json', '*.jsonl', '*.csv', '*.tsv', '*.log', '*.out', '*.txt']
lock = threading.Lock()


def record(**kw):
    kw['t'] = time.strftime('%Y-%m-%dT%H:%M:%S')
    with lock, open(OUT / 'status.jsonl', 'a') as f: f.write(json.dumps(kw) + '\n')


def done_tags():
    tags = {p.stem for p in (OUT / 'csv').glob('*.csv')}
    if (OUT / 'status.jsonl').exists():
        for line in open(OUT / 'status.jsonl'):
            r = json.loads(line)
            if r.get('state') in ('ok', 'no_claims', 'timeout', 'error', 'too_big'): tags.add(r['tag'])
    return tags


sizes = pd.read_csv(OUT / 'sizes.csv').sort_values('GB')
todo = [(m, int(p), gb) for m, p, gb in sizes[['model', 'paper', 'GB']].values if f'{m}__paper{int(p)}' not in done_tags()]
print(len(todo), 'submissions to do', flush=True)
q = queue.Queue(maxsize=2)


def downloader():
    from huggingface_hub import snapshot_download
    for m, p, gb in todo:
        tag = f'{m}__paper{p}'
        if gb > a.max_gb:
            record(tag=tag, state='too_big', GB=round(gb, 2)); continue
        dl = OUT / 'dl' / tag; sub = OUT / 'sub' / tag
        try:
            snapshot_download('prometheus-eval/into-the-unknown', repo_type='dataset', local_dir=str(dl),
                              allow_patterns=[f'file_systems/{m}/paper{p}/*'])
            src = dl / 'file_systems' / m / f'paper{p}'; sub.mkdir(parents=True, exist_ok=True)
            parts = sorted(src.glob('view.tar.part-*'))
            if parts:
                cat = subprocess.Popen(['cat'] + [str(x) for x in parts], stdout=subprocess.PIPE)
                subprocess.run(['tar', '-xf', '-', '-C', str(sub), '--wildcards'] + KEEP, stdin=cat.stdout, stderr=subprocess.DEVNULL)
                cat.wait()
            if (src / 'supplement.tar').exists():
                subprocess.run(['tar', '-xf', str(src / 'supplement.tar'), '-C', str(sub), '--wildcards'] + KEEP, stderr=subprocess.DEVNULL)
        except Exception as e:
            record(tag=tag, state='error', stage='download', msg=str(e)[:300]); shutil.rmtree(sub, ignore_errors=True); continue
        finally:
            shutil.rmtree(dl, ignore_errors=True)
        q.put((tag, sub, gb))
    for _ in range(a.workers): q.put(None)


def worker():
    while (item := q.get()) is not None:
        tag, sub, gb = item; t0 = time.time(); csv = OUT / 'csv' / f'{tag}.csv'
        try:
            r = subprocess.run([sys.executable, str(CHECK), str(sub), '--out', str(csv)], capture_output=True, text=True, timeout=a.timeout)
            meta = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
            state = 'ok' if csv.exists() else ('no_claims' if r.returncode == 0 else 'error')
            record(tag=tag, state=state, GB=round(gb, 2), secs=int(time.time() - t0), **{k: meta.get(k) for k in ('source', 'n_claims', 'n_evidence_values')},
                   **({'msg': r.stderr[-300:]} if state == 'error' else {}))
        except subprocess.TimeoutExpired:
            csv.unlink(missing_ok=True); record(tag=tag, state='timeout', GB=round(gb, 2), secs=a.timeout)
        finally:
            shutil.rmtree(sub, ignore_errors=True)


threads = [threading.Thread(target=downloader)] + [threading.Thread(target=worker) for _ in range(a.workers)]
for t in threads: t.start()
for t in threads: t.join()
print('finished', flush=True)
