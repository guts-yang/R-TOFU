#!/usr/bin/env bash
# After the full-training queue finishes, run full-data evaluation for all ten
# adapters on two H20 GPUs, then Hy4 judging and per-method summaries.
set -uo pipefail

ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
TRAIN_LOG="$ROOT/logs/full_queue"
EVAL_LOG="$ROOT/logs/full_eval"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$EVAL_LOG"

export PYTHONPATH="$CODE"
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FORGET=/jizhicfs/chenyliao/data/rtofu/forget10.json
RETAIN=/jizhicfs/chenyliao/data/rtofu/retain90.json

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$EVAL_LOG/queue.log"; }

wait_done() {
  log "waiting for training QUEUE_DONE"
  while [ ! -f "$TRAIN_LOG/QUEUE_DONE" ]; do
    sleep 120
  done
  log "training queue done; starting evaluation"
}

wait_gpu() {
  gpu="$1"
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, -v g="$gpu" '$1==g {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    [ "$used" -lt 1000 ] && return 0
    log "GPU ${gpu} busy (${used}MiB); wait"
    sleep 120
  done
}

eval_one() {
  gpu="$1"; method="$2"
  run="full_${method}"
  tag="fullEval_${method}"
  adapter="$ROOT/results/${run}/adapter"
  if [ ! -d "$adapter" ]; then
    log "SKIP ${method}: adapter missing"
    echo -e "${method}\tMISSING_ADAPTER" >> "$EVAL_LOG/status.tsv"
    return 0
  fi
  wait_gpu "$gpu"
  log "eval ${method} on GPU ${gpu}"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_eval.py" \
    --system "$run" --base /jizhicfs/chenyliao/models/sangyon/LRM-target \
    --adapter "$adapter" --tag "$tag" \
    --forget-file "$FORGET" --forget-task-id 1 \
    --n-forget 400 --n-retain 400 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --max-new-tokens 512 --batch-size 8 > "$EVAL_LOG/${method}.eval.log" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    log "EVAL FAILED ${method} rc=${rc}"
    echo -e "${method}\tEVAL_FAILED" >> "$EVAL_LOG/status.tsv"
    return 0
  fi
  "$PY" "$CODE/llm_judge.py" --tags "$tag" --limit-per-group 0 \
    --concurrency 8 --timeout 180 > "$EVAL_LOG/${method}.judge.log" 2>&1 || true
  (cd "$ROOT/diagnostics" && "$PY" summarize_diagnostic.py \
    --method "full_${method}" --tag "$tag") > "$EVAL_LOG/${method}.summary.log" 2>&1 || true
  log "done eval ${method}"
  echo -e "${method}\tDONE" >> "$EVAL_LOG/status.tsv"
}

wait_done
: > "$EVAL_LOG/status.tsv"

worker0() {
  eval_one 0 csda
  eval_one 0 rrbu
  eval_one 0 disco
  eval_one 0 ortho
  eval_one 0 sequ
}
worker1() {
  eval_one 1 eas
  eval_one 1 scope
  eval_one 1 cfa
  eval_one 1 ripple
  eval_one 1 bound
}

worker0 & W0=$!
worker1 & W1=$!
wait "$W0" "$W1"
log "ALL EVAL DONE"
touch "$EVAL_LOG/EVAL_DONE"
"$PY" "$CODE/aggregate_full_eval.py" > "$EVAL_LOG/aggregate.log" 2>&1 || true
log "aggregate written to $ROOT/diagnostics/FULL_EVAL_TABLE.md"
