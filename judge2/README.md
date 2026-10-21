# Second judge: Claude-Opus-5.5 re-grading of a stratified sample

**Purpose.** Every official verdict comes from one model (GPT-6-Astra, OpenAI). The two best-scoring
agents are OpenAI models. To test for judge–agent affinity, a different vendor's model re-grades a
stratified sample with the *identical* rubric, evidence protocol and grader.

**Instrument.** `src/grader/run_claude_code_judge.py` in the benchmark repo — the authors' own Claude
judge (Opus-5.5, effort max). It reuses the Codex runner's prompt, schema and frozen grader; only the
engine differs. Its docstring says the authors ran 420 such evaluations themselves, but those verdicts
are **not** in the public release (only `gpt-6-astra/` is). So this is new evidence, not a re-run.

**Sample.** `stratified_sample.csv`: 31 submissions, 3–4 per agent, every G1-passing submission of the
three passing agents included up to two each, remainder failing. Seeded (20261021).

**What it needs** (cannot run in the cloud workspace):
- the benchmark repo checked out, with `prepare_tasks.py` run
- the `file_systems/` subset for the 31 sampled submissions (each is the judge's full view of one
  submission; sizes vary, budget ~50–150 GB total)
- the `claude` CLI logged in to a Claude subscription (`claude login`); the script is quota-aware and
  will pace itself against the 5-hour/7-day windows
- a machine with ≥16 GB RAM and local disk for snapshots

**Commands** (run from the benchmark repo root):
```bash
# 1. fetch the sampled submissions' file systems
python - <<'PY'
import pandas as pd, subprocess
for m,p in pd.read_csv('../agent-integrity-analysis/judge2/stratified_sample.csv')[['model','paper']].values:
    subprocess.run(['huggingface-cli','download','prometheus-eval/into-the-unknown','--repo-type','dataset',
                    '--include',f'file_systems/{m}/paper{p}/*','--local-dir','.'],check=True)
PY
# 2. prepare a batch for just those agents/papers (one agent at a time keeps batches small)
python src/grader/run_claude_code_judge.py prepare        # prints BATCH_DIRECTORY=...
python src/grader/run_claude_code_judge.py rescope --root <BATCH_DIRECTORY> --reason "full view"
python src/grader/run_claude_code_judge.py pilot   --root <BATCH_DIRECTORY> --job <first job id>   # sanity check one
python src/grader/run_claude_code_judge.py launch  --root <BATCH_DIRECTORY>
python src/grader/run_claude_code_judge.py status  --root <BATCH_DIRECTORY>
# 3. grade each judgment with the frozen grader, exactly as for the official run
python src/grader/eval_artifacts/paper<i>/grading.py <judged_bundle.json>
```
Note: `prepare` builds the full 9×15 job list by default; restrict it with `--agents`/`--papers`
following `run_codex_judge.py prepare` (the Claude runner imports that job builder). Check the
`prepare()` signature before running — the CLI surface may change between commits.

**Analysis** (back in this repo): `scripts/05_judge_agreement.py` (to be written) computes per-node
agreement, Cohen's κ per gate, and a judge × agent-vendor interaction on G1.

**Decision rule.** Agreement ≥ 85% on counted G1 nodes and no vendor interaction → single judge
defensible, report as robustness check. Otherwise report the discrepancy as a finding; add a third,
non-US open-weight judge only if disagreement exceeds ~25%.
