# Second judge

This folder re-grades a stratified sample of 30 submissions with a second judge configuration: Claude Opus 5.5 running in the benchmark's Claude Code judge runner (`src/grader/run_claude_code_judge.py`). That runner reuses the official prompt, rubric, output schema, validator and deterministic grader. The judge model, the execution harness (a Claude Code session rather than a Codex thread) and the file-access restrictions all differ from the official GPT-6-Astra verdicts, so the comparison is between judge configurations, not an isolated test of vendor effects.

## Contents

| File | Content |
|---|---|
| `stratified_sample.csv` | The 30 sampled submissions: 3–4 per agent, including up to two integrity-gate passers per agent, each with an archived working directory of at most 5 GB |
| `verdicts/<agent>__paper<N>/repeat_XX/` | Second-judge outputs per submission and repeat (`grade.json`, `judgment_bundle.json`, node verdicts) |
| `agreement_by_submission.csv` | Node and gate agreement with the official judge, per submission |
| `disagreements.csv` | All counted nodes on which the two judges disagree |
| `vendor_test_by_submission.csv` | Per-submission G1 failure rates under each judge and their difference |
| `prepare_one.py` | Prepares a judge batch for one agent and one or more papers, with frozen inputs unchanged |
| `run_second_judge.sh` | Driver: downloads, stages, judges, archives and cleans up each submission |

## Running

Requirements:
- the benchmark repository at commit `612cdca`, with `prepare_tasks.py` run;
- the `claude` CLI, logged in;
- about 20 GB of free disk.

```bash
bash judge2/run_second_judge.sh setup                      # once
REPEATS=1 bash judge2/run_second_judge.sh batch            # all remaining submissions, parallel per agent
python scripts/05_judge_agreement.py <official_verdicts_dir> judge2/verdicts judge2/stratified_sample.csv
python scripts/06_vendor_test.py     <official_verdicts_dir> judge2/verdicts judge2/stratified_sample.csv
```

`<official_verdicts_dir>` is `artifacts/judge_results/gpt-6-astra` in the benchmark repository. The driver is resumable: submissions with a `DONE` marker are skipped. The first two submissions were graded with four repeats, the next two with two, and the rest with one.
