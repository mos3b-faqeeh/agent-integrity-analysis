#!/usr/bin/env bash
# Second-judge driver: for each sampled submission, download its judged file system from Hugging Face,
# stage it where the benchmark's Claude judge expects it, run the judge (4 repeats), grade, archive the
# verdicts into this repo, and delete the download. Resumable: finished submissions are skipped.
#
# Prereqs on the machine: git, python3 (3.10+), huggingface-cli, `claude` CLI logged in (claude login),
# ~6 GB free disk. First run:  bash judge2/run_second_judge.sh setup
#
# Layout (all under $WORK, default ~/itu-judge):
#   bench/        clone of prometheus-eval/into-the-unknown @ 612cdca, with prepare_tasks.py run
#   runs/         staged submissions, one at a time   (SOG_SUBMISSIONS)
#   judge_runs/   judge batches                        (SOG_JUDGE_RUNS)
#   dl/           raw Hugging Face downloads (deleted after staging)
set -euo pipefail
WORK="${WORK:-$HOME/itu-judge}"; REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SAMPLE="$REPO_DIR/judge2/stratified_sample.csv"; OUT="$REPO_DIR/judge2/verdicts"
BENCH="$WORK/bench"; export SOG_SUBMISSIONS="$WORK/runs" SOG_JUDGE_RUNS="$WORK/judge_runs"
PIN=612cdca4409cdd37578f52b09f01b3674fbd8f7e
export REPEATS="${REPEATS:-1,2}"   # judge repeats per submission; 4 for the first two, 2 thereafter (quota)
NREP=$(echo "$REPEATS" | tr ',' '\n' | wc -l | tr -d ' ')
log(){ printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

setup(){
  mkdir -p "$WORK" "$SOG_SUBMISSIONS" "$SOG_JUDGE_RUNS" "$WORK/dl" "$OUT"
  command -v claude >/dev/null || { echo "claude CLI not found: npm install -g @anthropic-ai/claude-code && claude login"; exit 1; }
  command -v huggingface-cli >/dev/null || pip install -q huggingface_hub
  [ -d "$BENCH/.git" ] || git clone -q https://github.com/prometheus-eval/into-the-unknown.git "$BENCH"
  git -C "$BENCH" checkout -q "$PIN"
  (cd "$BENCH" && python3 prepare_tasks.py)          # task code + data for all 15 papers (needed by the judge's frozen inputs)
  log "setup done in $WORK"
}

stage(){ # $1 agent  $2 paper
  local a="$1" p="$2" dl="$WORK/dl/$a/paper$p" dest="$SOG_SUBMISSIONS/$a/paper$p"
  rm -rf "$dl" "$dest"; mkdir -p "$dl" "$dest"
  huggingface-cli download prometheus-eval/into-the-unknown --repo-type dataset \
      --include "file_systems/$a/paper$p/*" --local-dir "$WORK/dl" >/dev/null
  local src="$WORK/dl/file_systems/$a/paper$p"
  cat "$src"/view.tar.part-* | tar -xf - -C "$dest"
  [ -f "$src/supplement.tar" ] && tar -xf "$src/supplement.tar" -C "$dest" || true
  # the archive holds proposal/ and workdir_outside_proposal/ ; the solver layout the judge wants is
  # <run>/proposal/ plus the rest of the working directory at <run>/ -- unfold it
  if [ -d "$dest/workdir_outside_proposal" ]; then
    (cd "$dest/workdir_outside_proposal" && tar -cf - .) | tar -xf - -C "$dest"; rm -rf "$dest/workdir_outside_proposal"
  fi
  rm -rf "$WORK/dl/file_systems/$a"
}

judge_one(){ # $1 agent  $2 paper
  local a="$1" p="$2" tag="$1__paper$2"
  [ -f "$OUT/$tag/DONE" ] && { log "skip $tag (done)"; return; }
  log "stage $tag"; stage "$a" "$p"
  cd "$BENCH"
  local root; root="$(BENCH="$BENCH" python3 "$REPO_DIR/judge2/prepare_one.py" "$a" "$p" | sed -n 's/^BATCH_DIRECTORY=//p' | tail -1)"
  [ -n "$root" ] || { echo "prepare_one printed no BATCH_DIRECTORY"; exit 1; }
  python3 src/grader/run_claude_code_judge.py rescope --root "$root" --reason "full view"
  python3 src/grader/run_claude_code_judge.py launch  --root "$root" || true
  # wait until all $NREP cells are complete at the TOP level of state.json (not a stage's status) and have grade.json
  cells_done(){ python3 - "$root" <<'PY'
import json,sys,glob,os
root=sys.argv[1]; n=0
for st in glob.glob(f"{root}/*/P*/repeat_*/state.json"):
    try: s=json.load(open(st))
    except Exception: continue
    if s.get("status")=="complete" and os.path.exists(os.path.join(os.path.dirname(st),"grade.json")): n+=1
print(n)
PY
  }
  until [ "$(cells_done)" = "$NREP" ]; do
    if [ -f "$root/PAUSE.json" ]; then
      log "paused: $(tr -d '\n' < "$root/PAUSE.json" | cut -c1-160)"; sleep 900
      rm -f "$root/PAUSE.json"; python3 src/grader/run_claude_code_judge.py resume --root "$root" || true
    else sleep 120; fi
  done
  mkdir -p "$OUT/$tag"
  for cell in "$root"/*/P*/repeat_*; do
    [ -d "$cell" ] || continue
    local rep; rep="$(basename "$cell")"; mkdir -p "$OUT/$tag/$rep"
    for f in verdicts judgment_bundle.json grade.json state.json; do [ -e "$cell/$f" ] && cp -r "$cell/$f" "$OUT/$tag/$rep/"; done
  done
  cp "$root/manifest.json" "$OUT/$tag/" 2>/dev/null || true
  date -u +%FT%TZ > "$OUT/$tag/DONE"
  rm -rf "$SOG_SUBMISSIONS/$a/paper$p" "$root/snapshots" "$root"/*/P*/repeat_*/workspace_*
  log "done $tag"
}

run_all(){
  tail -n +2 "$SAMPLE" | while IFS=, read -r a p rest; do judge_one "$a" "$p"; done
  log "all submissions judged -> $OUT"
}

case "${1:-run}" in
  setup) setup ;;
  one)   judge_one "$2" "$3" ;;
  run)   run_all ;;
  *) echo "usage: $0 setup | run | one <agent> <paper>"; exit 1 ;;
esac
