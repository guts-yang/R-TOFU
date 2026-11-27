#!/usr/bin/env bash
# v2 evaluation queue: full 400+400, four strategies, retry-failed judge.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
TRAIN_LOG="$ROOT/logs/v2_queue"
LOG="$ROOT/logs/v2_eval"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
export OMP_NUM_THREADS=8
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FORGET=/jizhicfs/chenyliao/data/rtofu/forget10.json
RETAIN=/jizhicfs/chenyliao/data/rtofu/retain90.json

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

while [ ! -f "$TRAIN_LOG/V2_QUEUE_DONE" ]; do
  log "waiting for V2_QUEUE_DONE"
  sleep 120
done

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
  gpu="$1"; m="$2"
  run="v2_${m}"; tag="v2Eval_${m}"
  adapter="$ROOT/results/${run}/adapter"
  if [ ! -d "$adapter" ]; then
    log "SKIP ${m}: adapter missing"
    echo -e "${m}\tMISSING_ADAPTER" >> "$LOG/status.tsv"
    return 0
  fi
  wait_gpu "$gpu"
  log "eval ${m} GPU${gpu}"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_eval.py" \
    --system "$run" --base /jizhicfs/chenyliao/models/sangyon/LRM-target \
    --adapter "$adapter" --tag "$tag" \
    --forget-file "$FORGET" --forget-task-id 1 \
    --n-forget 400 --n-retain 400 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --max-new-tokens 512 --batch-size 8 > "$LOG/${m}.eval.log" 2>&1 || true
  "$PY" "$CODE/llm_judge.py" --tags "$tag" --limit-per-group 0 \
    --concurrency 8 --timeout 180 --max-retries 2 --retry-failed \
    > "$LOG/${m}.judge.log" 2>&1 || true
  (cd "$ROOT/diagnostics" && "$PY" summarize_diagnostic.py \
    --method "$run" --tag "$tag") > "$LOG/${m}.summary.log" 2>&1 || true
  echo -e "${m}\tDONE" >> "$LOG/status.tsv"
  log "done eval ${m}"
}

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
"$PY" "$CODE/aggregate_full_eval.py" --tag-prefix v2Eval \
  --out FULL_EVAL_TABLE_v2.md > "$LOG/aggregate.log" 2>&1 || true
log "ALL V2 EVAL DONE"
touch "$LOG/V2_EVAL_DONE"
