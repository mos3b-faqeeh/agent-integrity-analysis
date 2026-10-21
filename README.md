# Misreporting, not fabrication: an independent analysis of AI research agents' integrity failures

Independent secondary analysis of the released judge verdicts and agent trajectories from
**Into the Unknown: Benchmarking AI agents on open scientific research problems**
(Kim et al., 2026, arXiv:2610.19159; code: github.com/prometheus-eval/into-the-unknown;
data: huggingface.co/datasets/prometheus-eval/into-the-unknown).

Author: Mosab Alfaqeeh, PhD. Status: work in progress, preprint forthcoming.

## What this repository contains

| Path | Content |
|---|---|
| `scripts/` | Analysis scripts, numbered in run order |
| `data/derived/` | Tables *derived* by these scripts from the public release (submission-level gates, per-node integrity verdicts with judge reasons, trajectory features) |
| `judge2/` | Second-judge (Claude) protocol, stratified sample and verdicts |
| `figures/` | Figures used in the paper |
| `docs/` | Notes and the evolving manuscript |

## What it does NOT contain

The benchmark tasks, the original scientific papers, the 135 agent-written papers, the
trajectories and the official GPT-6-Astra verdicts are **not redistributed** here. They are
owned by the benchmark authors and the papers' publishers (Apache-2.0 for code and rubrics;
publisher terms for the original papers; mixed licenses for agent outputs). Fetch them with
the benchmark's own loader; every script takes the local paths as arguments.

```bash
git clone https://github.com/prometheus-eval/into-the-unknown.git            # judge verdicts in artifacts/
huggingface-cli download prometheus-eval/into-the-unknown --repo-type dataset \
    --include "trajectories/*.json" "trajectories/*/*.json" "trajectories/*.csv" --local-dir hfdata
```

## Reproduce

```bash
pip install pandas numpy scipy statsmodels
python scripts/01_gate_summary.py           into-the-unknown/artifacts/judge_results/gpt-6-astra
python scripts/02_extract_integrity_nodes.py into-the-unknown/artifacts/judge_results/gpt-6-astra
python scripts/03_runtime_fixed_effects.py   into-the-unknown/artifacts/judge_results/gpt-6-astra hfdata
python scripts/04_trajectory_features.py     hfdata data/derived/trajectory_features_claude_agents.csv
```

Benchmark snapshot used: commit `612cdca` of prometheus-eval/into-the-unknown (2026-10-19).

## Citation of the benchmark

Kim, S., Geng, J., Lee, Y.-J., ... Asai, A., Neubig, G., Welleck, S. (2026).
*Into the Unknown: Benchmarking AI agents on open scientific research problems.* arXiv:2610.19159.

## License

Code and derived tables: MIT. See the benchmark's own licenses for everything it releases.
