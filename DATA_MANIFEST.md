# Data manifest

Where each result in the paper comes from, and which file holds it. All paths are relative to the repository root. Python 3.13 with the packages in `requirements.txt`.

## 1. Checker implementation

| Item | File |
|---|---|
| Claim extraction, evidence index and result-file parser, bulk filter, Level-1 value matching, provenance score, decoy calibration | `checker/claimcheck.py` |
| Frozen operating points (strict τ = 0.12, ρ = 0.1; balanced; broad) | `checker/operating_points.json` |
| Stratified sampling of claims for labelling | `checker/make_label_sheet.py` (development), `checker/make_confirm_sheet.py` (confirmation) |
| Benchmark-wide driver (resumable) | `analysis/run_checker_all.py` |

Decoy offsets are `CAL_OFFSETS` (±2, ±4, ±6, ±8, ±10 units in the last reported digit) and `TEST_OFFSET` (+7, used only to measure decoy acceptance) in `checker/claimcheck.py`.

## 2. Human annotation data

| Item | File |
|---|---|
| Development claims as shown to the annotator (paper context, three best-matching evidence entries) | `labels/claims_to_label.csv` (194 claims; C001–C010 were practice items and are excluded) |
| Checker verdicts for the development claims, kept out of the annotator's view | `labels/claims_to_label_KEY.csv` |
| Development labels, first annotator (184) | `labels/mosab_labels.csv` |
| Self-consistency re-labelling of 20 development claims | `labels/recheck.csv` (`first`, `second`) |
| Confirmation claims (72) with sampling strata | `labels/confirm/confirm_claims.csv` |
| Confirmation labels, first annotator (72) | `labels/confirm/mosab_confirm_labels.csv`. `changed_after_prompt` marks the four labels revised for consistency with the written rules |
| Confirmation labels, second annotator (48) | `labels/confirm/annotatorB_labels.csv` |
| Double-coded claims with both annotators and the first annotator's original labels | `labels/confirm/agreement_A_vs_B.csv` (`A_orig` = label before revision) |
| Labelling interface | `labels/tool/` |

## 3. Sampling information and weights

- **Development sample:** 10 submissions drawn; one had no extractable claims, so the claims come from 9. Strata are submission × whether the checker run the sheet was drawn from certified the claim. The population counts N per stratum come from that run, `data/derived/checker_v0_dev_claims.csv` (claims with ≥ 2 significant digits).
- **Confirmation sample:** one unused submission per agent (9 drawn; astra-6 dropped before any claims were viewed, so 8). `N_stratum` and `n_stratum` are recorded per claim in `labels/confirm/confirm_claims.csv`.
- **Weights:** each claim's weight is N/n within its submission × stratum. The weighted shares estimate proportions among **eligible claims (≥ 2 significant digits) in the sampled submissions**. They are not extrapolated to all 135 submissions. The development denominators n include the ten practice claims later excluded; recomputing without them changes the weighted wrong-source share from 80.60% to 80.92% (both 81%). With the first annotator's four original (pre-revision) confirmation labels it is 78.45%.
- **Per-claim weights for all 256 labelled claims:** `data/derived/labels_with_weights.csv`, written by `analysis/label_distribution.py`.

## 4. Analysis outputs by table and figure

| Paper item | Script | Data |
|---|---|---|
| Fig. 2 (rubric families), Table A.1 (fixed effects) | `scripts/01`–`03`, `analysis/make_figures.py` | `data/derived/integrity_nodes.csv`, `data/derived/submissions.csv` |
| Table 2 (agents) | `scripts/01_gate_summary.py` | `data/derived/submissions.csv` |
| Table 4 (labels; 47/53 = 89% raw, 81% weighted) | `analysis/label_distribution.py` | `labels/`, `data/derived/checker_v0_dev_claims.csv` |
| Table 6 (development) | `analysis/score_checker.py data/derived/checker_v1_dev_claims.csv data/derived/checker_v0_dev_claims.csv` | `data/derived/checker_vs_human.csv` |
| Table 6 (confirmation), Fig. 3 | `analysis/score_confirm.py data/derived/confirmation_run` | `data/derived/confirmation_results.csv`, `data/derived/confirmation_checker_vs_human.csv` |
| Tables 7, 8, 9 | `analysis/tables_precision_ablation_baselines.py` | `data/derived/baselines_scored.csv`, `data/derived/checker_v1_dev_claims_scorers.csv` |
| Embedding baseline | `analysis/embedding_baseline.py` | `data/derived/embedding_baseline_scored.csv` |
| LLM-verifier baseline | `baselines/llm_verifier/run_llm_verifier.py` | `baselines/llm_verifier/prompts.jsonl`, `baselines/llm_verifier/results.jsonl` |
| Table 10, Fig. 4 | `analysis/benchmark_traceability.py data/derived/benchmark_run` | `data/derived/benchmark_run/csv/` (per-claim output for the 99 submissions), `data/derived/benchmark_traceability_by_*.csv` |
| Table 11, Fig. 5 | `scripts/05_judge_agreement.py`, `scripts/06_vendor_test.py` | `judge2/*.csv` |
| Table A.2 (misses) | see note | `data/derived/baselines_scored.csv` |
| Tables B.1 and B.2 (sensitivity checks, processing disposition) | `analysis/sensitivity_checks.py` | `data/derived/labels_with_weights.csv`, `data/derived/benchmark_run/`, `judge2/vendor_test_by_submission.csv`, `data/derived/submissions.csv` |

**Note on Table A.2.** The 37 uncertified traceable claims are those on the development tuning split.
- "Score just below threshold" (13) follows directly from the data: p ≤ 0.1 and S < 0.12.
- The other 24 have p > 0.1. They were split by manual inspection into "decoys match equally well" (6) and "another entry scores best" (18), by comparing the best-matching entry with the source the annotator identified. That per-claim split was not recorded as a file.

## 5. Judge evaluation records

| Item | File |
|---|---|
| Stratified sample of 30 submissions | `judge2/stratified_sample.csv` |
| Second-judge outputs per submission and repeat (`grade.json`, `judgment_bundle.json`, run state) | `judge2/verdicts/<agent>__paper<N>/repeat_XX/` |
| Run metadata (model, CLI version, isolation settings) | `judge2/verdicts/<agent>__paper<N>/manifest.json` |
| Node-level agreement, disagreements, per-submission G1 failure rates | `judge2/agreement_by_submission.csv`, `judge2/disagreements.csv`, `judge2/vendor_test_by_submission.csv` |
| Official judge verdicts | not redistributed; `artifacts/judge_results/gpt-6-astra` in the benchmark repository at commit `612cdca` |

## 6. Reproducibility

- **Environment:** `requirements.txt`.
- **Run order:** `REPRODUCE_CACHED.md` (included files only) and "Reproducing the results" in `README.md` (original release).
- **Processing logs:**
  - benchmark-wide run status per submission: `data/derived/benchmark_run/status.jsonl` (135 submissions: 99 checked, 3 completed with no eligible claims, 15 timeouts, 2 errors, 16 over the 10 GB size limit);
  - checker console output for the confirmation submissions: `data/derived/confirmation_run/ccc/*.stdout`.
- **Not included:** the benchmark's tasks, agent working directories, trajectories and official verdicts, which belong to the benchmark authors. Scripts that need them take their local paths as arguments.

## 7. Processing status and checker semantics

- **Processing status of the 135 submissions** (`data/derived/benchmark_run/status.jsonl`): 99 checked with eligible claims, 3 with no eligible claims, 15 timeouts, 2 errors and 16 over the size limit. The 99 are not a random subset, so per-agent certified shares are conditional on processing completion.
- **`untraced`:** at Level 2 this means no eligible non-bulk entry matches the value. Of the 14,577 eligible claims in the benchmark-wide run, 529 match only bulk entries. The "Untraced" column of Table 10 uses the Level 1 indicator (no match in any indexed entry), so it is not affected.

## 8. Source data versions

- Benchmark repository: commit `612cdca4409cdd37578f52b09f01b3674fbd8f7e`.
- Hugging Face dataset `prometheus-eval/into-the-unknown`: revision `270caa1c1ed78528c0e8a0eb94e128be8ce2ff4c` (18 October 2026), as recorded by the download cache. The only later commit, `d2b75cbee507927f09dedb2d8d80c372190e7c73`, edits the dataset card and leaves the data unchanged.
- Paper versions: arXiv:2610.38691 v1 and v2 correspond to the repository commits of 28 and 31 October 2026. `paper/` holds the current source.

