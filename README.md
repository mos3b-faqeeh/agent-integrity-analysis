# Misreporting, not fabrication: an independent analysis of AI research agents' integrity failures

**Mosab Alfaqeeh, PhD** — Kingston, Ontario, Canada · [Google Scholar](https://scholar.google.com/citations?user=Ewi0-RgAAAAJ)

Independent analysis of how AI research agents fail integrity checks, using the released judge verdicts
and agent trajectories of the *Into the Unknown* benchmark (Kim et al., 2026). Findings so far: agents
misreport rather than fabricate; run length does not explain integrity, agent identity does; the
benchmark's harness behaved differently per agent. Preprint forthcoming.

## Cite this work

If you use these analyses, derived tables, scripts or the second-judge verdicts, please cite:

```bibtex
@misc{alfaqeeh2026misreporting,
  author = {Alfaqeeh, Mosab},
  title  = {Misreporting, not fabrication: an independent analysis of AI research agents' integrity failures},
  year   = {2026},
  howpublished = {\url{https://github.com/mos3b-faqeeh/agent-integrity-analysis}},
  note   = {Preprint forthcoming; arXiv identifier will be added here}
}
```
GitHub's **"Cite this repository"** button (from `CITATION.cff`) gives the same reference in APA/BibTeX.

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

## Acknowledgement

The underlying benchmark, tasks, agent papers and official verdicts are the work of Kim et al. (2026),
*Into the Unknown: Benchmarking AI agents on open scientific research problems*, arXiv:2610.19159
(github.com/prometheus-eval/into-the-unknown). This repository redistributes none of it; see above.

## License

Code and derived tables: MIT. See the benchmark's own licenses for everything it releases.
