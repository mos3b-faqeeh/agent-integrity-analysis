"""Prepare a one-submission batch for the benchmark's Claude judge.

run_claude_code_judge.prepare() takes no arguments and hard-wires all 105 submissions / 420 jobs
(and a parity check against a Codex batch that we do not have). This wrapper narrows the two job
builders it calls -- astra.discover_sources and astra.make_jobs -- to a single <agent>/paper<i>,
then calls prepare() unchanged, so the frozen inputs, prompts, schema and grader are identical.

usage (from the benchmark repo root, with SOG_SUBMISSIONS / SOG_JUDGE_RUNS set):
    python judge2/prepare_one.py <agent-dir> <paper>      # e.g. opus-5 7
prints BATCH_DIRECTORY=... like the original.
"""
import sys, os
from pathlib import Path

agent_dir, paper = sys.argv[1], int(sys.argv[2])
REPEATS = [int(x) for x in os.environ.get('REPEATS', '1,2').split(',')]
bench = Path(os.environ.get('BENCH', os.getcwd())).resolve()
sys.path.insert(0, str(bench / 'src' / 'grader'))
os.chdir(bench)

import run_codex_judge as astra            # noqa: E402
import run_claude_code_judge as cc         # noqa: E402

key = next((k for k, _, d in astra.MODELS if d == agent_dir), None)
if key is None:
    sys.exit(f'unknown agent dir {agent_dir}; choose from {[d for _, _, d in astra.MODELS]}')

_ds, _mj = astra.discover_sources, astra.make_jobs
astra.discover_sources = lambda keys=None, papers=None: _ds((key,), [paper])
astra.make_jobs = lambda keys=None, papers=None, repeats=None: _mj((key,), [paper], REPEATS)
# the parity check compares job lists against an existing Codex batch; skip by hiding Codex batches
astra.PREFIX = astra.PREFIX + '__none__'
# some code paths read base.JUDGE_RUNS.glob(astra.PREFIX*) -- the renamed prefix matches nothing

root = cc.prepare()
# fix the manifest's hard-coded totals so status/launch bookkeeping matches the one-submission batch
import json  # noqa: E402
m = json.load(open(root / 'manifest.json'))
m.update(total_submissions=1, total_evaluations=len(REPEATS), total_rubric_sessions=2 * len(REPEATS), repeats=len(REPEATS),
         model_order=[key], papers=[paper], repeats_selected=REPEATS,
         scope=f'Single submission {agent_dir}/paper{paper}, repeats {REPEATS}; same inputs as the Codex judge.')
# scope_order(m) (rescope/launch dispatch) rebuilds ids from model_order x papers x repeats_selected and
# requires them to equal the job list, hence the three keys above.
json.dump(m, open(root / 'manifest.json', 'w'), indent=2)
s = json.load(open(root / 'status.json')); s['total'] = len(REPEATS)
json.dump(s, open(root / 'status.json', 'w'), indent=2)
print(f'BATCH_DIRECTORY={root}', flush=True)
