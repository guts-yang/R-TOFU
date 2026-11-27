#!/usr/bin/env bash
# Wait for the retried RRBU/DISCO/RIPPLE adapters, then run their full eval and
# refresh the aggregate table.
set -uo pipefail

ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/retry_eval"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
export OMP_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FORGET=/jizhicfs/chenyliao/data/rtofu/forget10.json
RETAIN=/jizhicfs/chenyliao/data/rtofu/retain90.json

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

for m in rrbu disco ripple; do
  while [ ! -d "$ROOT/results/full_${m}/adapter" ]; do
    log "waiting for full_${m}/adapter"
    sleep 120
  done
done
log "all retry adapters present"

run_eval() {
  gpu="$1"; m="$2"
  tag="fullEval_${m}"
  log "eval ${m} on GPU ${gpu}"
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, -v g="$gpu" '$1==g {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    [ "$used" -lt 1000 ] && break
    log "GPU ${gpu} busy (${used}MiB); wait"
    sleep 120
  done
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_eval.py" \
    --system "full_${m}" --base /jizhicfs/chenyliao/models/sangyon/LRM-target \
    --adapter "$ROOT/results/full_${m}/adapter" --tag "$tag" \
    --forget-file "$FORGET" --forget-task-id 1 \
    --n-forget 400 --n-retain 400 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --max-new-tokens 512 --batch-size 8 > "$LOG/${m}.eval.log" 2>&1 || true
  "$PY" "$CODE/llm_judge.py" --tags "$tag" --limit-per-group 0 \
    --concurrency 8 --timeout 180 > "$LOG/${m}.judge.log" 2>&1 || true
  (cd "$ROOT/diagnostics" && "$PY" summarize_diagnostic.py \
    --method "full_${m}" --tag "$tag") > "$LOG/${m}.summary.log" 2>&1 || true
  log "done ${m}"
}

run_eval 0 rrbu
run_eval 1 disco
run_eval 0 ripple
"$PY" "$CODE/aggregate_full_eval.py" > "$LOG/aggregate.log" 2>&1 || true
log "retry eval complete and aggregate refreshed"
touch "$LOG/RETRY_EVAL_DONE"
