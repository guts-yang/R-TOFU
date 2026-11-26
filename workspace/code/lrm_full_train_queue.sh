#!/usr/bin/env bash
# Wait for GPU 0 to become free, then run all ten LRM full-data training jobs
# on two H20 GPUs. Diagnostic-only; no ARIS gate or claim.
set -uo pipefail

ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/full_queue"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"

export PYTHONPATH="$CODE"
export OMP_NUM_THREADS=8
export MKL_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

# Continuous GPU monitor until the queue is stopped.
monitor_gpu() {
  while true; do
    {
      date -u +%Y-%m-%dT%H:%M:%SZ
      nvidia-smi --query-gpu=index,name,utilization.gpu,memory.used,memory.total \
        --format=csv,noheader
      nvidia-smi --query-compute-apps=pid,process_name,used_memory \
        --format=csv,noheader 2>/dev/null || true
      echo '---'
    } >> "$LOG/gpu_monitor.log"
    sleep 60
  done
}

# Wait for one GPU's memory to drain. Per-GPU waiting lets the idle GPU start
# immediately while the other one is still occupied by an external job.
wait_for_gpu_index() {
  gpu="$1"
  log "waiting for GPU ${gpu} to drain"
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, -v g="$gpu" '$1==g {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    if [ "$used" -lt 1000 ]; then
      log "GPU ${gpu} is free (used=${used}MiB)"
      return 0
    fi
    log "GPU ${gpu} busy (used=${used}MiB); sleeping 60s"
    sleep 60
  done
}

train_one() {
  gpu="$1"; method="$2"; steps="$3"; nf="$4"; nr="$5"
  run_id="full_${method}"
  out="$LOG/${method}.log"
  log "start ${method} on GPU ${gpu}: steps=${steps} nf=${nf} nr=${nr}"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_train_hooked.py" \
    --method "$method" --steps "$steps" --grad-accum 1 \
    --n-forget "$nf" --n-retain "$nr" --max-len 512 --lr 1e-4 \
    --run-id "$run_id" --hook-mode full > "$out" 2>&1
  rc=$?
  if [ "$rc" -eq 0 ]; then
    log "done ${method} rc=0"
    echo -e "${method}\t${gpu}\tDONE\t${run_id}" >> "$LOG/queue_status.tsv"
  else
    log "FAILED ${method} rc=${rc}; see ${out}"
    echo -e "${method}\t${gpu}\tFAILED\t${run_id}" >> "$LOG/queue_status.tsv"
  fi
  return 0
}

monitor_gpu &
MON_PID=$!
log "monitor pid ${MON_PID}"
: > "$LOG/queue_status.tsv"

# Two workers. CSDA gets one forget row per step because its hook does
# per-step activation patching; the other methods use 32+32 sampled batches.
worker0() {
  wait_for_gpu_index 0
  train_one 0 csda 400 1 8
  train_one 0 rrbu 400 8 8
  train_one 0 disco 300 8 8
  train_one 0 ortho 200 16 16
  train_one 0 sequ 200 16 16
}
worker1() {
  wait_for_gpu_index 1
  train_one 1 eas 300 16 16
  train_one 1 scope 300 16 16
  train_one 1 cfa 300 16 16
  train_one 1 ripple 300 8 8
  train_one 1 bound 300 16 16
}

worker0 & W0=$!
worker1 & W1=$!
wait "$W0" "$W1"
kill "$MON_PID" 2>/dev/null || true
log "ALL DONE"
touch "$LOG/QUEUE_DONE"
