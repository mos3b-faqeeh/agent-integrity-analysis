# Beyond fabrication: Misattributed numbers in papers written by AI research agents

**Mosab Alfaqeeh**¹ · **Omar Mohammed Horani**¹ · **Mou'th Hourani**¹ · **Hashem Alfaqeeh**²

¹ Al-Ahliyya Amman University, Amman, Jordan · ² Binghamton University, State University of New York, USA

Code, data and paper source for the study *Beyond fabrication: Misattributed numbers in papers written by AI research agents*.

---

## Overview

AI research agents can now run experiments and write complete papers. Recent benchmarks show that many agent-written papers fail integrity checks. However, such verdicts usually come from a single LLM judge, and they record *that* a paper failed, not *how*.

This repository provides four things:

1. **A re-analysis of all 540 released judgments** (9 agents × 15 tasks × 4 repeats), at the level of individual rubric criteria.
2. **256 human-labelled numerical items** from 18 selected submissions (211 evaluable claims after excluding 45 settings or extraction errors; 17 submissions contribute evaluable labels). Each label distinguishes numbers with no source in the agent's files from numbers drawn from the wrong experiment, metric or run.
3. **A deterministic claim-to-evidence checker.** It traces each number in a paper back to the agent's own result files and certifies the claim only when the number *belongs to the result it claims to describe*.
4. **A cross-vendor second-judge study** that re-grades 30 submissions with the benchmark's own grading pipeline.

## Key results

| Finding | Evidence |
|---|---|
| Failures concern the match between write-up and work | Code–paper alignment fails in 52% of counted criteria and number traceability in 38%; the specific checks for hard-coded values, external code and replication fail in ≤1% |
| Unsupported numbers are mostly misattributed, not absent | 47 of 53 unsupported evaluable claims were wrong-source (88.7% unweighted); 80.6% after weighting eligible claims **within the selected submissions** (exploratory cluster-bootstrap 95% interval 60–99%), not an estimate for all 135 submissions |
| Value matching cannot detect misattribution | Checking whether a value appears accepts about 87–95% of unsupported claims in the labelled samples, and 87% of decoy values among the 1,351 eligible development claims |
| Provenance checking certifies with high precision | 78 of 85 certified claims were judged traceable (91.8%, exact 95% CI 84–97%); 27 of 29 on held-out submissions; inter-annotator κ = 0.89 on 48 double-coded claims |
| Non-verification is not evidence of falsehood | The checker certifies about 23% of eligible claims (weighted); many uncertified claims are traceable (19 of 31 held-out, 61 of 95 development) |
| Checker and LLM verifier are complementary | An LLM verifier recovers more traceable claims but accepts 36% of untraceable ones (checker: 13%); when both accept a claim, 51 of 52 are traceable (development test split and confirmation combined; 27 of 27 on confirmation alone) |
| Outcomes depend on the judge configuration | On 30 sampled submissions, a second judge configuration (different model and harness) has lower G1 node-failure rates (−5.4 points, Wilcoxon p = 0.014) and passes 12 submissions against the official judge's 6 (exact McNemar p = 0.070); because model and harness differ together, the comparison cannot isolate vendor effects |

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
requirements.txt    Python package versions used for the reported results
DATA_MANIFEST.md    Which script and file produce each table and figure
REPRODUCE_CACHED.md Commands that recompute the results from the included files
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

A `supported` verdict is strong evidence, not a guarantee, that the number is backed by the recorded result it describes: in the labelled data, 78 of 85 certified claims were traceable. It does **not** mean the experiment itself is sound. `untraced` means that no eligible **non-bulk** result entry matches the value; the value may still occur in bulk entries (529 of 14,577 claims in the benchmark-wide run). A non-`supported` verdict should be routed to human review; it is not evidence that the number is false.

## Reproducing the results

**From the files in this repository (no benchmark download).** Labels, sampling weights, per-claim checker outputs, second-judge verdicts and derived tables are all included, so the main results can be recomputed directly. See [`REPRODUCE_CACHED.md`](REPRODUCE_CACHED.md) for the commands; `DATA_MANIFEST.md` maps every table and figure to its script and data.

**From the original benchmark release.** The steps that read the official judge verdicts or the agents' working directories need the benchmark data, which are not redistributed here:

```bash
git clone https://github.com/prometheus-eval/into-the-unknown.git          # official judge verdicts (artifacts/)
git -C into-the-unknown checkout 612cdca4409cdd37578f52b09f01b3674fbd8f7e
hf download prometheus-eval/into-the-unknown --repo-type dataset \
    --revision 270caa1c1ed78528c0e8a0eb94e128be8ce2ff4c \
    --include "file_systems/*" --local-dir hfdata                           # agent working directories (very large)
```

The Hugging Face revision is the one recorded by our downloads; the only later commit (`d2b75cb`) changes the dataset card, not the data. Run everything from the repository root; scripts that read the raw release take its local paths as arguments (see each docstring).

| Step | Command |
|---|---|
| Judge re-analysis | `scripts/01_gate_summary.py`, `scripts/02_extract_integrity_nodes.py`, `scripts/03_runtime_fixed_effects.py` (raw release) |
| Label distribution and weights (Table 4) | `analysis/label_distribution.py` |
| Checker vs. human labels (Tables 6–9) | `analysis/score_checker.py`, `analysis/score_confirm.py`, `analysis/tables_precision_ablation_baselines.py` |
| Baselines | `analysis/embedding_baseline.py`, `baselines/llm_verifier/run_llm_verifier.py` |
| Benchmark-wide run (Table 10) | `analysis/run_checker_all.py` (raw release), then `analysis/benchmark_traceability.py data/derived/benchmark_run` |
| Second judge (Table 11) | `judge2/run_second_judge.sh` (raw release, `claude` CLI), then `scripts/05_judge_agreement.py` and `scripts/06_vendor_test.py` |
| Figures | `analysis/make_figures.py` |

## Data and licensing

- **Not redistributed:** the benchmark tasks, the original papers, the agent-written submissions, the trajectories and the official judge verdicts. These belong to the benchmark authors and the respective publishers; obtain them from the original release.
- **Included:** derived tables, human labels, second-judge verdicts and all code.
- **Code licence:** MIT (see `LICENSE`). Derived tables that reproduce benchmark content remain subject to the benchmark's own terms.

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
