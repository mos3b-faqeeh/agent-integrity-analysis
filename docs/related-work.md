# Related work scan (2026-10-24)

Question: has anyone already (a) shown that AI research agents' integrity failures are mostly misreporting rather than fabrication, or (b) built and human-validated a checker that traces numbers in agent-written papers back to the agent's own result files?

Answer so far: **no direct overlap found.** The closest pieces each cover one part.

## Closest work and how we differ

| Work | What it does | Gap we fill |
|---|---|---|
| Kim et al. 2026, *Into the Unknown* (arXiv 2610.19159) | The benchmark itself; a single GPT judge assigns integrity verdicts | We re-analyse the released verdicts, decompose the failures, add human-labelled claim-level evidence, a second judge, and a deterministic checker |
| Yin et al. 2026, *Artifact-centered Claim-aware Observability for Autonomous Scientific Agents* (arXiv 2608.18312, COLM LM4Sci workshop) | Position/design: agents should emit claim-aware traces; sketches a hypothetical "claim_numeric_checker" | Our checker is implemented, run on real agent outputs, and validated by two annotators on fresh data; it works *without* special traces |
| Ding et al. 2026, *Autonomous Research Agents: A Survey of AI Scientists and the Verification Gap* (arXiv 2608.05179) | Survey: verification, not capability, is the bottleneck; few systems release traces | Supports our motivation; we supply an empirical measurement |
| Eulig 2026, *Correct Answer, Wrong Mechanism* (arXiv 2606.23175, position) | 28 episodes: agents defend mechanisms their own data contradicts | Mechanism-level honesty; we measure number-level provenance at benchmark scale |
| Epoch AI 2026, *InnovationEval* (Oct 2026) | Agents farmed seeds and omitted selection; headline gains shrank about 21× after review | Independent evidence that the dominant failure is selective/misattributed reporting, not invented data. This matches our thesis; cite as convergent |
| Kirgis, Kapoor, Narayanan et al. 2026, CRUX shadow evaluation (arXiv 2607.27191) | Agent on unpublished NeurIPS papers; failure modes; no fabricated data reported | Convergent evidence |
| Luo et al. 2026, *Unearned Passes* (arXiv 2609.34262) | Audits passing trajectories for reward hacking in agentic benchmarks | Trajectory-level exploits; ours is paper-vs-artifact consistency |
| Song 2026, *Cross-Model Review in LLM Verification* (arXiv 2610.01471) | A cross-vendor reviewer finds partly different errors; reviewer capability matters | Related to our second-judge design; no self-preference test |
| paperjudge (GitHub, Rashid0002) | Checks paper claims against the paper's *own tables*; reports planted-error catch rates of ~0–28% | Internal consistency only, no execution artifacts; similar "certify, can't accuse" behaviour |
| MLR-Bench (Chen et al., NeurIPS 2025 D&B, arXiv 2505.19955) | LLM judge for open-ended ML research; reports agents fabricating or invalidating results | Earlier claim of "fabrication", judge-based only. Our human labels refine it: most failures are misattribution |
| CheckThat! 2026 numerical claim verification (arXiv 2607.25069) | Numeric fact-checking of public claims against web evidence | Same task family, different evidence source; useful for framing in IP&M |

## Classic consistency checkers to cite (from background knowledge; verify references before submission)

- statcheck (Nuijten et al., 2016): recomputes p-values from reported test statistics in psychology papers.
- GRIM test (Brown & Heathers, 2017): checks whether reported means are possible given the sample sizes.

Both check internal consistency. Neither traces a number back to the run that produced it.

## Positioning sentence

Prior work either *proposes* claim-to-artifact tracing without building it (Yin et al.), checks a paper against *itself* (statcheck, GRIM, paperjudge), or relies on an *LLM judge's* reading (Into the Unknown, MLR-Bench). We provide the first human-validated, deterministic claim-to-evidence measurement on a public agent benchmark. With it we show that the dominant integrity failure is misattribution of real numbers, which naive matching cannot detect.

## Still to do

- Read the Into the Unknown related-work section for anything it cites on traceability.
- Check ScientistOne (Meng et al., 2026) and PaperBench / ReplicationBench for claim-provenance components.
- Re-run this scan right before submission (the field moves monthly).
