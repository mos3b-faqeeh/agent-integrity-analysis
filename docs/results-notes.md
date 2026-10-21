# Results notes (working, 2026-10-21)

Data: official GPT-6-Astra verdicts (540 judgments = 9 agents × 15 tasks × 4 repeats), consensus grading;
trajectories for the four Claude-agent-SDK agents (60 runs). Benchmark snapshot: prometheus-eval/into-the-unknown @ 612cdca.

## 1. Headline gates (consensus, strict)

| Agent | G1 integrity | G2 complete | G3 bar | median hrs |
|---|---|---|---|---|
| astra-6 | 11/15 | 1 | 0 | 1.3 |
| sol-5.6 | 6/15 | 0 | 0 | 2.9 |
| opus-5.5 | 4/15 | 0 | 0 | 5.3 |
| opus-5, opus-4.8, fable-5, kimi-k3, deepseek-v4-pro, glm-5.3 | 0/15 | 0 | 0 | 4.8–19.5 |

540 judgment outcomes: integrity_failure 450, incomplete 86, below_scientists_bar 4.

## 2. Integrity failures are misreporting, not fabrication

2,376 counted G1 nodes; 469 fail (all `violation_detected`; 438 high-confidence, 31 medium).

| Rubric family | fail / counted | rate |
|---|---|---|
| code_paper_alignment | 118 / 225 | 52% |
| number_traceability | 122 / 324 | 38% |
| integrity (execution claims) | 72 / 279 | 26% |
| held_fixed_disclosure | 32 / 99 | 32% |
| pre_stated_method | 27 / 99 | 27% |
| test_set_integrity | 23 / 81 | 28% |
| selective_reporting | 13 / 252 | 5% |
| baseline_honesty | 12 / 144 | 8% |
| no_hardcoded_values | 2 / 135 | 1% |
| no_external_code | 1 / 81 | 1% |
| no_replication_of_published_method | 0 / 99 | 0% |

Reading: the "cheating" nodes almost never fire; the "write-up matches the work" nodes fire constantly.
Typical judge reasons: 400 epochs claimed, 320 run; ten seeds claimed, nine used; "identical schedule"
claimed, records show different schedules; ZZ term described, never applied in the final propagation.

Agent split on code_paper_alignment failure rate: astra-6 0%, sol-5.6 16%, opus-5.5 28% | opus-5 68%,
opus-4.8 72%, fable-5 84%, kimi-k3 76%, deepseek 72%, glm 56%.

## 3. Run length does not explain integrity; agent identity does

Raw: Spearman(log hours, R_integrity) = −0.37, p < 1e-4. G1-pass median 2.3 h vs fail 9.2 h.
OLS R_integrity ~ log(hours) + agent FE + task FE (HC1): log-hours coef −0.61, p = 0.59; R² = 0.77.
Adding attempts and log(events): all n.s. Within-agent Spearman: all |ρ| < 0.45, all p > 0.10.
Logit G1 ~ log hours + agent FE on the three agents with variance (n = 45): coef −0.56, p = 0.12.

## 4. Judge reliability (single judge, four repeats)

Unanimous 4/4 on 9,570 / 10,638 counted nodes = 90.0% (G1 89.5%, G2 90.8%, G3 89.3%).
11 / 135 submissions have a G1 verdict that differs across repeats.

## 5. opus-5 vs opus-5.5: a harness confound, not a clean version effect

Paired on the same 15 tasks (Wilcoxon):

| feature | opus-5 | opus-5.5 | p |
|---|---|---|---|
| R_integrity | 62.5 | 92.3 | 0.001 |
| hours | 7.5 | 5.3 | 0.39 |
| tool calls | 620 | 636 | 0.26 |
| bash python / 100 calls | 35 | 43 | 0.06 |
| bash reads of logs / 100 calls | 31.5 | 30.8 | 0.93 |
| harness attempts (restarts) | 6 | 1 | 0.001 |
| non-empty thinking blocks | 0 of 5,038 | 1,841 of 9,000 | — |
| tool errors / 100 calls | 2.9 | 1.7 | <0.001 |

The runner (`src/solver/run_agent_sdk.py`) has a "completion judge" that checks the paper and restarts the
agent on failure. For opus-5 that completion judge *itself failed to run* 59 times over 15 tasks
("completion judge failed to run"); 3/15 opus-5 runs reached `completed`. For opus-5.5: 1 such failure,
15/15 completed. opus-4.8 and fable-5 each had 25 completion-judge failures.

Within opus-5 the number of restarts does not predict integrity (pooled agent-demeaned ρ = −0.05, p = 0.69),
so restarts are not *the* mechanism — but the two models were not run under equivalent conditions, and the
opus-5 trajectories carry no thinking text, so the version comparison cannot be read as a controlled
behavioural contrast. Report as: (a) a harness-sensitivity finding — the benchmark's own infrastructure
behaved differently per agent — and (b) a limitation on any version-to-version claim.

Open question worth a paragraph: the only behavioural signal that separates opus-5.5 from the other Claude
agents is visible reasoning that mentions verification (~4.3 per 100 tool calls); whether that reflects a
model change or a logging change is not determinable from the release.

## 6. Things that did not work

- Embedding-clustering the 469 judge reasons (MiniLM, k-means): silhouette ≤ 0.03. The judge writes to a
  fixed template; rubric families are the taxonomy.
- Parsing the Codex, OpenHands, Kimi and DeepSeek harness logs into comparable features: formats differ
  (Codex `item` objects, OpenHands `ActionEvent` lines, raw stdout for the two CLIs). Not attempted yet.
