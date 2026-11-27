#!/usr/bin/env bash
# Repair DISCO after the libcublasLt SIGFPE at its step-100 dev forward.
# Wait until GPU0 has finished the async queue's SEQU job, then rerun with
# dev disabled (the trigger), falling back to the proxy hook if still needed.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/disco_retry"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
FORGET=/jizhicfs/chenyliao/data/rtofu/forget10.json

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

wait_for_gpu0() {
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, '$1==0 {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    [ "$used" -lt 3000 ] && return 0
    log "GPU0 busy (${used}MiB)"
    sleep 60
  done
}

# Do not race the queue's SEQU job: wait until it has been scheduled and is gone.
log "waiting for SEQU to be scheduled/finish"
while ! grep -q '^sequ' "$ROOT/logs/pair_async/status.tsv" 2>/dev/null; do
  sleep 60
done
while pgrep -f 'diagnostic_train_v2.py --method sequ' >/dev/null 2>&1 || \
      pgrep -f 'diagnostic_eval.py --system v2_sequ' >/dev/null 2>&1; do
  log "SEQU still running"
  sleep 60
done
log "SEQU finished; repairing DISCO on GPU0"
wait_for_gpu0

train() {
  hook="$1"
  CUDA_VISIBLE_DEVICES=0 "$PY" "$CODE/diagnostic_train_v2.py" \
    --method disco --steps 300 --grad-accum 1 \
    --n-forget 2 --n-retain 2 --max-len 512 --lr 1e-4 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --consistency-weight 0.1 --dev-ratio 0 --eval-every 1000 \
    --early-stop-patience 3 --run-id v2_disco --hook-mode "$hook" \
    > "$LOG/disco.${hook}.log" 2>&1
}

# The full DISCO path already trapped in libcublasLt at step 128 even with
# dev disabled. Use the proxy path; it is explicitly labelled PROXY_FALLBACK.
train proxy
if [ ! -d "$ROOT/results/v2_disco/adapter" ]; then
  log "DISCO repair FAILED"
  exit 1
fi
log "DISCO adapter ready; evaluating"
CUDA_VISIBLE_DEVICES=0 "$PY" "$CODE/diagnostic_eval.py" \
  --system v2_disco --base /jizhicfs/chenyliao/models/sangyon/LRM-target \
  --adapter "$ROOT/results/v2_disco/adapter" --tag v2Eval_disco \
  --forget-file "$FORGET" --forget-task-id 1 \
  --n-forget 400 --n-retain 400 \
  --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
  --max-new-tokens 512 --batch-size 8 > "$LOG/disco.eval.log" 2>&1 || true
"$PY" "$CODE/llm_judge.py" --tags v2Eval_disco --limit-per-group 0 \
  --concurrency 10 --timeout 180 --max-retries 2 --retry-failed \
  > "$LOG/disco.judge.log" 2>&1 || true
(cd "$ROOT/diagnostics" && "$PY" summarize_diagnostic.py \
  --method v2_disco --tag v2Eval_disco) > "$LOG/disco.summary.log" 2>&1 || true
"$PY" "$CODE/aggregate_full_eval.py" --tag-prefix v2Eval \
  --out FULL_EVAL_TABLE_v2.md > "$LOG/aggregate.log" 2>&1 || true
log "DISCO repair + eval done"
touch "$LOG/DISCO_DONE"
