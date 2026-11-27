#!/usr/bin/env bash
# Evaluate whatever v2 adapters the retry queue produced.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/v2_retry_eval"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
FORGET=/jizhicfs/chenyliao/data/rtofu/forget10.json
RETAIN=/jizhicfs/chenyliao/data/rtofu/retain90.json

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

while [ ! -f "$ROOT/logs/v2_retry/V2_RETRY_DONE" ]; do
  log "waiting V2_RETRY_DONE"
  sleep 120
done

wait_gpu0() {
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, '$1==0 {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    [ "$used" -lt 5000 ] && return 0
    log "GPU0 busy (${used}MiB); wait"
    sleep 120
  done
}

for m in eas scope cfa csda rrbu disco ortho sequ ripple bound; do
  adapter="$ROOT/results/v2_${m}/adapter"
  if [ ! -d "$adapter" ]; then
    log "SKIP ${m}: no adapter"
    echo -e "${m}\tMISSING" >> "$LOG/status.tsv"
    continue
  fi
  wait_gpu0
  tag="v2Eval_${m}"
  log "eval ${m}"
  CUDA_VISIBLE_DEVICES=0 "$PY" "$CODE/diagnostic_eval.py" \
    --system "v2_${m}" --base /jizhicfs/chenyliao/models/sangyon/LRM-target \
    --adapter "$adapter" --tag "$tag" \
    --forget-file "$FORGET" --forget-task-id 1 \
    --n-forget 400 --n-retain 400 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --max-new-tokens 512 --batch-size 8 > "$LOG/${m}.eval.log" 2>&1 || true
  "$PY" "$CODE/llm_judge.py" --tags "$tag" --limit-per-group 0 \
    --concurrency 8 --timeout 180 --max-retries 2 --retry-failed \
    > "$LOG/${m}.judge.log" 2>&1 || true
  (cd "$ROOT/diagnostics" && "$PY" summarize_diagnostic.py \
    --method "v2_${m}" --tag "$tag") > "$LOG/${m}.summary.log" 2>&1 || true
  echo -e "${m}\tDONE" >> "$LOG/status.tsv"
done
"$PY" "$CODE/aggregate_full_eval.py" --tag-prefix v2Eval \
  --out FULL_EVAL_TABLE_v2.md > "$LOG/aggregate.log" 2>&1 || true
log "V2 RETRY EVAL DONE"
touch "$LOG/V2_RETRY_EVAL_DONE"
