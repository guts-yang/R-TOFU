#!/usr/bin/env bash
# Orchestrator for EXPERIMENT_PLAN.md. All outputs under workspace/.
set -euo pipefail

PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
WS=/usr/local/workspace/R-TOFU/workspace
cd "$WS"
mkdir -p results logs code
export TOKENIZERS_PARALLELISM=false
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$WS/logs/run_all.log"; }

# fp32 is mandatory: bf16/fp16 + KV-cache decode step SIGFPEs on this host.
EVAL_EXTRA="--batch-size 4"  # decode_eval.py hardcodes fp32; do not pass --dtype

sanity() {
  log "M0 sanity start"
  $PY code/decode_eval.py --model target --tag sanity --n-forget 2 --n-retain 1 \
      --strategies DefaultCoT,ZeroThink --max-new-tokens 64 --batch-size 2 $EVAL_EXTRA
  log "M0 sanity done"
}

m1() {
  log "M1 baseline eval start"
  for s in target r2mu01 r2mu05; do
    $PY code/decode_eval.py --model "$s" --n-forget 40 --n-retain 20 \
        --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink $EVAL_EXTRA
  done
  log "M1 baseline eval done"
}

m2() {
  log "M2 invariant training start"
  $PY code/train_invariant.py --run-id ours-inv \
      --strategies DefaultCoT,LessThink,ZeroThink --lambda-cons 1.0 \
      --beta-retain 0.5 --epochs 2 --n-forget 40 --n-retain 40
  $PY code/train_invariant.py --run-id ctrl-single \
      --strategies DefaultCoT --lambda-cons 0.0 \
      --beta-retain 0.5 --epochs 2 --n-forget 40 --n-retain 40
  log "M2 invariant training done"
}

m3() {
  log "M3 method eval start"
  for s in ours-inv ctrl-single; do
    $PY code/decode_eval.py --model "$s" --n-forget 40 --n-retain 20 \
        --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink $EVAL_EXTRA
  done
  log "M3 method eval done"
}

m4() {
  log "M4 budget grid start"
  for s in target r2mu01 ours-inv; do
    $PY code/decode_eval.py --model "$s" --n-forget 20 --n-retain 0 \
        --budget-grid 64,128,256,512 $EVAL_EXTRA
  done
  log "M4 budget grid done"
}

recompute() {
  log "M5a recompute entity metrics start"
  $PY code/recompute_leak.py
  log "M5a recompute entity metrics done"
}

judge() {
  log "M5b LLM-as-judge (Hy4) start"
  $PY code/llm_judge.py --limit-per-group 16 --concurrency 4
  log "M5b LLM-as-judge done"
}

analyze() {
  log "analysis start"
  $PY code/analyze_results.py --delta 0.1
  log "analysis done"
}

case "${1:-all}" in
  sanity)  sanity ;;
  m1)      m1 ;;
  m2)      m2 ;;
  m3)      m3 ;;
  m4)      m4 ;;
  recompute) recompute ;;
  judge)   recompute; judge ;;
  analyze) analyze ;;
  all)     sanity; m1; m2; m3; m4; recompute; judge; analyze ;;
  *) echo "usage: $0 {sanity|m1|m2|m3|m4|judge|analyze|all}" >&2; exit 2 ;;
esac
