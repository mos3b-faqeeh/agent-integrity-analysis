# LLM-verifier baseline

This baseline asks an LLM to label the same 211 real claims the human annotators labelled. It gets the same written guide and the same evidence the annotators saw (paper context plus the top-3 matching entries), and nothing else: no human labels, no checker verdicts, no file access.

Run it on a machine where the `claude` CLI is logged in:

```bash
cd ~/agent-integrity-analysis && git pull
python3 baselines/llm_verifier/run_llm_verifier.py --limit 3    # quick test
python3 baselines/llm_verifier/run_llm_verifier.py              # all 211 (resumable)
```

Output goes to `baselines/llm_verifier/results.jsonl`, one line per claim. Commit it, or tell Claude it is done.
