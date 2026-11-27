#!/usr/bin/env bash
# v2 training queue: safe CoT + 4-strategy consistency + dev early stop/best.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/v2_queue"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
export OMP_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

wait_gpu() {
  gpu="$1"
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, -v g="$gpu" '$1==g {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    [ "$used" -lt 30000 ] && return 0
    log "GPU ${gpu} busy (${used}MiB); wait"
    sleep 120
  done
}

run_one() {
  gpu="$1"; method="$2"; steps="$3"; nf="$4"; nr="$5"; maxlen="$6"
  run="v2_${method}"
  log "start ${run} GPU${gpu} steps=${steps} nf=${nf} nr=${nr} maxlen=${maxlen}"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_train_v2.py" \
    --method "$method" --steps "$steps" --grad-accum 1 \
    --n-forget "$nf" --n-retain "$nr" --max-len "$maxlen" --lr 1e-4 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --consistency-weight 0.1 --dev-ratio 0.10 --eval-every 50 \
    --early-stop-patience 4 --run-id "$run" --hook-mode full \
    > "$LOG/${method}.log" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    log "done ${run}"
    echo -e "${method}\t${gpu}\tDONE\t${run}" >> "$LOG/status.tsv"
  else
    log "FAILED ${run} rc=${rc}"
    echo -e "${method}\t${gpu}\tFAILED\t${run}" >> "$LOG/status.tsv"
  fi
  return 0
}

worker0() {
  wait_gpu 0
  run_one 0 csda 200 1 2 256
  run_one 0 rrbu 200 2 2 256
  run_one 0 disco 200 2 2 256
  run_one 0 ortho 150 4 4 384
  run_one 0 sequ 150 4 4 384
}
worker1() {
  wait_gpu 1
  run_one 1 eas 200 4 4 384
  run_one 1 scope 200 4 4 384
  run_one 1 cfa 200 4 4 384
  run_one 1 ripple 150 2 2 256
  run_one 1 bound 200 4 4 384
}

worker0 & W0=$!
worker1 & W1=$!
wait "$W0" "$W1"
log "ALL V2 DONE"
touch "$LOG/V2_QUEUE_DONE"
