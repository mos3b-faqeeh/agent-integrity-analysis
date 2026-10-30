# Beyond fabrication: Misattributed numbers in papers written by AI research agents

**Mosab Alfaqeeh**¹ · **Omar Mohammed Horani**¹ · **Mou'th Hourani**¹ · **Hashem Alfaqeeh**²

¹ Al-Ahliyya Amman University, Amman, Jordan · ² Binghamton University, State University of New York, USA

Code, data and paper source for the study *Beyond fabrication: Misattributed numbers in papers written by AI research agents*.

---

## Overview

AI research agents can now run experiments and write complete papers. Recent benchmarks show that many agent-written papers fail integrity checks. However, such verdicts usually come from a single LLM judge, and they record *that* a paper failed, not *how*.

This repository provides four things:

1. **A re-analysis of all 540 released judgments** (9 agents × 15 tasks × 4 repeats), at the level of individual rubric criteria.
2. **256 human-labelled numerical claims** from 18 submissions. Each label distinguishes numbers with no source in the agent's files from numbers drawn from the wrong experiment, metric or run.
3. **A deterministic claim-to-evidence checker.** It traces each number in a paper back to the agent's own result files and certifies the claim only when the number *belongs to the result it claims to describe*.
4. **A cross-vendor second-judge study** that re-grades 30 submissions with the benchmark's own grading pipeline.

## Key results

| Finding | Evidence |
|---|---|
| Failures concern the match between write-up and work, not overt cheating | Code–paper alignment fails in 52% of criteria and number traceability in 38%; hard-coded values, external code and replication fail in ≤1% |
| Unsupported numbers are mostly misattributed, not absent | 47 of 53 unsupported claims exist in the agent's files but for a different experiment, metric or run (81% population-weighted) |
| Value matching cannot detect misattribution | Checking whether a value appears accepts 87–95% of unsupported claims and 88% of decoy values |
| Provenance checking certifies with high precision | 78 of 85 certified claims are traceable (92%, exact 95% CI 84–97%); 27 of 29 on held-out submissions; inter-annotator κ = 0.89 |
| Non-verification is not evidence of falsehood | 57–72% of claims the checker does not certify are traceable |
| Checker and LLM verifier are complementary | An LLM verifier recovers more traceable claims but accepts 36% of untraceable ones (checker: 13%); when both agree, 51 of 52 claims are traceable |
| Rankings are robust to the judge; pass rates are not | A second judge from a different vendor preserves the agent ranking but passes 12 of 30 submissions where the official judge passes 6 |

## Repository structure

```
checker/            Claim-to-evidence checker
  claimcheck.py       claim extraction, evidence index, Level-1 matching, provenance score, decoy calibration
  operating_points.json   frozen strict / balanced / broad settings
  make_label_sheet.py, make_confirm_sheet.py   stratified sampling of claims for labelling
analysis/           Evaluation of the checker, baselines, benchmark-wide run, figures
baselines/          LLM-verifier baseline (prompts, runner, results)
scripts/            Re-analysis of the official judgments and the second-judge comparison (numbered in run order)
judge2/             Second-judge protocol, stratified sample, verdicts and agreement tables
labels/             Human labels (development, re-check, confirmation, second annotator) and labelling interface
data/derived/       Tables derived from the public benchmark release
paper/              LaTeX source of the manuscript and figures
```

## Using the checker

```bash
pip install pandas numpy scipy
python checker/claimcheck.py <submission_dir> --out claims.csv
```

`<submission_dir>` is an agent's working directory containing the paper's LaTeX source and its result files. Each row of the output is one numerical claim, with:
- its Level-1 match status;
- its provenance score and calibration p-value;
- the verdict at the strict operating point (`L2`: `supported` / `unattributed` / `untraced`);
- the best-matching evidence entry, for audit.

A `supported` verdict means the number is backed by a recorded result. It does **not** mean the experiment itself is sound. A non-`supported` verdict should be routed to human review; it is not evidence that the number is false.

## Reproducing the results

The benchmark data are not redistributed here (see below). Obtain them first:

```bash
git clone https://github.com/prometheus-eval/into-the-unknown.git      # judge verdicts (artifacts/)
git -C into-the-unknown checkout 612cdca
huggingface-cli download prometheus-eval/into-the-unknown --repo-type dataset \
    --include "file_systems/*" --local-dir hfdata                       # agent working directories (large)
```

Then run the steps below. Every script takes local paths as arguments; see each file's docstring.

| Step | Command |
|---|---|
| Judge re-analysis | `scripts/01_gate_summary.py`, `scripts/02_extract_integrity_nodes.py`, `scripts/03_runtime_fixed_effects.py` |
| Checker vs. human labels | `analysis/score_checker.py`, `analysis/score_confirm.py` |
| Baselines | `analysis/embedding_baseline.py`, `baselines/llm_verifier/run_llm_verifier.py` |
| Benchmark-wide run | `analysis/run_checker_all.py`, then `analysis/benchmark_traceability.py` |
| Second judge | `judge2/run_second_judge.sh`, then `scripts/05_judge_agreement.py` and `scripts/06_vendor_test.py` |
| Figures | `analysis/make_figures.py` |

## Data and licensing

- **Not redistributed:** the benchmark tasks, the original papers, the agent-written submissions, the trajectories and the official judge verdicts. These belong to the benchmark authors and the respective publishers; obtain them from the original release.
- **Included:** derived tables, human labels, second-judge verdicts and all code.
- **Code licence:** MIT (see `LICENSE`).

## Citation

```bibtex
@misc{alfaqeeh2026beyond,
  author        = {Alfaqeeh, Mosab and Horani, Omar Mohammed and Hourani, Mou'th and Alfaqeeh, Hashem},
  title         = {Beyond fabrication: Misattributed numbers in papers written by AI research agents},
  year          = {2026},
  eprint        = {2610.38691},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  doi           = {10.48550/arXiv.2610.38691},
  url           = {https://arxiv.org/abs/2610.38691}
}
```

GitHub's **"Cite this repository"** button gives the same reference.

The benchmark data used in this study are from:

> Kim, S., et al. (2026). arXiv:2610.19159.

## Contact

Mosab Alfaqeeh — m.alfaqeeh@ammanu.edu.jo
