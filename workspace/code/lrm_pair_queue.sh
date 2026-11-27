#!/usr/bin/env bash
# Two-GPU sequential pipeline: one method at a time per GPU, train -> full eval
# -> Hy4 -> summary -> next method. Batch sizes are deliberately small.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/pair_queue"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
export OMP_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FORGET=/jizhicfs/chenyliao/data/rtofu/forget10.json
RETAIN=/jizhicfs/chenyliao/data/rtofu/retain90.json

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

wait_gpu() {
  gpu="$1"
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, -v g="$gpu" '$1==g {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    [ "$used" -lt 3000 ] && return 0
    log "GPU ${gpu} busy (${used}MiB); wait"
    sleep 60
  done
}

params() {
  case "$1" in
    csda) echo "400 1 2 256" ;;
    rrbu) echo "300 2 2 256" ;;
    disco) echo "300 2 2 256" ;;
    ortho) echo "250 2 2 256" ;;
    sequ) echo "250 2 2 256" ;;
    eas) echo "300 2 2 256" ;;
    scope) echo "300 2 2 256" ;;
    cfa) echo "300 2 2 256" ;;
    ripple) echo "250 2 2 256" ;;
    bound) echo "300 2 2 256" ;;
  esac
}

train_one() {
  gpu="$1"; m="$2"
  read -r steps nf nr maxlen <<< "$(params "$m")"
  run="v2_${m}"
  log "TRAIN ${run} GPU${gpu} steps=${steps} nf=${nf} nr=${nr} maxlen=${maxlen}"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_train_v2.py" \
    --method "$m" --steps "$steps" --grad-accum 1 \
    --n-forget "$nf" --n-retain "$nr" --max-len "$maxlen" --lr 1e-4 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --consistency-weight 0.1 --dev-ratio 0.10 --eval-every 100 \
    --early-stop-patience 3 --run-id "$run" --hook-mode full \
    > "$LOG/${m}.train.log" 2>&1
  rc=$?
  if [ "$rc" -ne 0 ] || [ ! -d "$ROOT/results/${run}/adapter" ]; then
    log "TRAIN_FAILED ${run} rc=${rc}"
    echo -e "${m}\tTRAIN_FAILED" >> "$LOG/status.tsv"
    return 1
  fi
  log "TRAIN_DONE ${run}"
  echo -e "${m}\tTRAIN_DONE" >> "$LOG/status.tsv"
  return 0
}

eval_one() {
  gpu="$1"; m="$2"
  run="v2_${m}"; tag="v2Eval_${m}"
  wait_gpu "$gpu"
  log "EVAL ${tag} GPU${gpu}"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_eval.py" \
    --system "$run" --base /jizhicfs/chenyliao/models/sangyon/LRM-target \
    --adapter "$ROOT/results/${run}/adapter" --tag "$tag" \
    --forget-file "$FORGET" --forget-task-id 1 \
    --n-forget 400 --n-retain 400 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --max-new-tokens 512 --batch-size 8 > "$LOG/${m}.eval.log" 2>&1 || true
  "$PY" "$CODE/llm_judge.py" --tags "$tag" --limit-per-group 0 \
    --concurrency 8 --timeout 180 --max-retries 2 --retry-failed \
    > "$LOG/${m}.judge.log" 2>&1 || true
  (cd "$ROOT/diagnostics" && "$PY" summarize_diagnostic.py \
    --method "$run" --tag "$tag") > "$LOG/${m}.summary.log" 2>&1 || true
  log "EVAL_DONE ${tag}"
  echo -e "${m}\tEVAL_DONE" >> "$LOG/status.tsv"
}

worker() {
  gpu="$1"; shift
  for m in "$@"; do
    wait_gpu "$gpu"
    if train_one "$gpu" "$m"; then
      wait_gpu "$gpu"
      eval_one "$gpu" "$m"
    fi
  done
}

: > "$LOG/status.tsv"
worker 0 csda rrbu disco ortho sequ & W0=$!
worker 1 eas scope cfa ripple bound & W1=$!
wait "$W0" "$W1"
"$PY" "$CODE/aggregate_full_eval.py" --tag-prefix v2Eval \
  --out FULL_EVAL_TABLE_v2.md > "$LOG/aggregate.log" 2>&1 || true
log "ALL PAIR QUEUE DONE"
touch "$LOG/PAIR_DONE"
