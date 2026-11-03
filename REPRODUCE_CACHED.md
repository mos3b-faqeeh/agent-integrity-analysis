# Reproducing the results from the included files

These commands recompute the paper's human-label, checker and benchmark-wide results from the files in this repository. They do not need the benchmark download, API keys, agent runs or LLM judges. Run them from the repository root, with Python 3.13 and the packages in `requirements.txt`.

```bash
python -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt

python analysis/label_distribution.py                       # Table 4; writes data/derived/labels_with_weights.csv
python analysis/score_checker.py data/derived/checker_v1_dev_claims.csv data/derived/checker_v0_dev_claims.csv   # Table 6, development
python analysis/score_confirm.py data/derived/confirmation_run   # Table 6 confirmation, Fig. 3 inputs (about a minute)
python analysis/tables_precision_ablation_baselines.py      # Tables 7, 8, 9 and decoy acceptance rates
python analysis/benchmark_traceability.py data/derived/benchmark_run   # Table 10, Fig. 4 inputs
python analysis/sensitivity_checks.py                       # Appendix B, Tables B.1 and B.2
python analysis/make_figures.py                             # Figures 2-5
```

## What to expect

| Quantity | Value |
|---|---|
| Labelled items / evaluable claims | 256 / 211 (45 settings or extraction errors) |
| Wrong-source among unsupported claims | 47 / 53 = 88.7% unweighted; 80.6% weighted within the selected submissions |
| Strict checker precision | 78 / 85 pooled; 27 / 29 on the confirmation sample |
| Decoy acceptance, strict | 1.3% of the 1,351 eligible development claims |
| Benchmark-wide run | 99 submissions checked, 14,577 eligible claims; 529 match only bulk entries |
| Certified share vs official integrity score | Spearman ρ = 0.22 (p = 0.028, n = 99) |

The bootstrap intervals use fixed seeds (1 for the development analysis, 7 for the confirmation analysis). CSV row order and floating-point printing can differ between package versions, so compare numbers rather than file hashes.

## What needs the original benchmark release

Re-extracting claims from the agents' working directories (`analysis/run_checker_all.py`), the judge re-analysis (`scripts/01`–`03`) and re-running the second judge (`judge2/run_second_judge.sh`) need the original release; see "Reproducing the results" in `README.md` for the pinned Git commit and Hugging Face revision.

Two items cannot be recomputed from files:
- The split of 24 missed claims into 6 and 18 in Table A.2 was made by manual inspection, and the per-claim decisions were not saved.
- The development balanced and broad bootstrap interval endpoints come from an earlier version of the bootstrap code. Rerunning the current scripts gives slightly different endpoints.
