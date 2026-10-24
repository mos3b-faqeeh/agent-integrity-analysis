# Abstract — draft 1 (2026-10-24)

**Misreporting, not fabrication: an independent analysis of AI research agents' integrity failures**

Mosab Alfaqeeh

AI research agents can now run experiments and write papers end to end. Their reports, however, often fail integrity checks. On the recent *Into the Unknown* benchmark, 114 of 135 agent-written papers failed the integrity gate, yet the benchmark's verdicts come from a single LLM judge, and the nature of the failures is unclear.

We re-analyse all 540 released judgments across nine agents and fifteen open research tasks. We pair this with claim-level human evidence and a deterministic claim-to-evidence checker that traces each number in an agent's paper back to the agent's own result files.

Three findings stand out:
1. The judge's failing criteria are concentrated in alignment between write-up and work (52% failure on code–paper alignment, 38% on number traceability). Criteria targeting overt cheating almost never fire (≤1%).
2. In 256 human-labelled claims from 18 submissions, about four in five unsupported numbers (81%, population-weighted) do exist in the agent's files, but come from a different experiment, metric or run. Only a minority have no source at all.
3. Naive value matching accepts 87–95% of these misattributed numbers. Our calibrated checker, frozen on development data and confirmed on fresh submissions, certifies claims with 95% precision against two annotators (κ = 0.89), at the cost of covering only about a third of traceable claims.

Agent identity, not run length, explains integrity outcomes once task and agent effects are controlled.

The results reframe agent integrity failures as misreporting rather than fabrication. They show that verifying agent-written science requires provenance, not value matching. We release all code, labels and derived data.

**Keywords:** AI research agents; research integrity; claim verification; provenance; LLM-as-a-judge; reproducibility

---
Notes for revision:
- ~260 words; IP&M allows up to 250. Trim the method sentence if needed.
- Second-judge results are not in yet; add one clause if the comparison finishes ("a second judge from a different vendor agrees on X%").
- "81%" is population-weighted; the unweighted count is 47 wrong-source vs. 6 not-found (89%). The paper must state both.
