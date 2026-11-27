#!/usr/bin/env bash
# Retry v2 methods after GPU release, one at a time, with fallback batch sizes.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/v2_retry"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
export OMP_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

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

run_one() {
  method="$1"; steps="$2"; nf="$3"; nr="$4"; maxlen="$5"; extra="${6:-}"
  run="v2_${method}"
  wait_gpu0
  log "start ${run} steps=${steps} nf=${nf} nr=${nr} maxlen=${maxlen}"
  CUDA_VISIBLE_DEVICES=0 "$PY" "$CODE/diagnostic_train_v2.py" \
    --method "$method" --steps "$steps" --grad-accum 1 \
    --n-forget "$nf" --n-retain "$nr" --max-len "$maxlen" --lr 1e-4 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --consistency-weight 0.1 --dev-ratio 0.10 --eval-every 50 \
    --early-stop-patience 4 --run-id "$run" --hook-mode full $extra \
    > "$LOG/${method}.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    log "done ${run}"
    echo -e "${method}\tDONE\t${run}" >> "$LOG/status.tsv"
    return 0
  fi
  log "retry ${run} with fallback batch (rc=${rc})"
  wait_gpu0
  CUDA_VISIBLE_DEVICES=0 "$PY" "$CODE/diagnostic_train_v2.py" \
    --method "$method" --steps "$steps" --grad-accum 1 \
    --n-forget 1 --n-retain 1 --max-len 192 --lr 1e-4 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --consistency-weight 0.1 --dev-ratio 0.10 --eval-every 50 \
    --early-stop-patience 4 --run-id "$run" --hook-mode full $extra \
    > "$LOG/${method}.fallback.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    log "done ${run} (fallback)"
    echo -e "${method}\tDONE_FALLBACK\t${run}" >> "$LOG/status.tsv"
  else
    log "FAILED ${run} rc=${rc}"
    echo -e "${method}\tFAILED\t${run}" >> "$LOG/status.tsv"
  fi
  return 0
}

: > "$LOG/status.tsv"
run_one eas 200 2 2 256
run_one scope 200 2 2 256
run_one cfa 200 2 2 256
run_one csda 200 1 1 192
run_one rrbu 200 2 2 256
run_one disco 200 2 2 256
run_one ortho 150 2 2 256
run_one sequ 150 2 2 256
run_one ripple 150 2 2 256
run_one bound 200 2 2 256
log "ALL V2 RETRY DONE"
touch "$LOG/V2_RETRY_DONE"
