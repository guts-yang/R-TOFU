#!/usr/bin/env bash
# Queue R2MU 0.1/0.5/1.0 full re-evaluation after the current v2 pipeline.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
LOG="$ROOT/logs/r2mu_full"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
export PYTHONPATH="$CODE"
FORGET=/jizhicfs/chenyliao/data/rtofu/forget10.json
RETAIN=/jizhicfs/chenyliao/data/rtofu/retain90.json
CKPT=/jizhicfs/chenyliao/checkpoints
TOKENIZER=/jizhicfs/chenyliao/models/sangyon/LRM-target

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/queue.log"; }

# Wait for the current v2 training/eval queue to finish.
while [ ! -f "$ROOT/logs/pair_async/PAIR_ASYNC_DONE" ]; do
  log "waiting PAIR_ASYNC_DONE"
  sleep 120
done
# DISCO repair may still be using GPU0 after PAIR_ASYNC_DONE.
while pgrep -f 'lrm_disco_retry.sh|diagnostic_train_v2|diagnostic_eval' >/dev/null 2>&1; do
  log "GPU pipeline still active"
  sleep 60
done

wait_gpu() {
  gpu="$1"
  while true; do
    used=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
      | awk -F, -v g="$gpu" '$1==g {gsub(/ /,"",$2); print $2}')
    used=${used:-0}
    [ "$used" -lt 3000 ] && return 0
    log "GPU ${gpu} busy (${used}MiB)"
    sleep 60
  done
}

run_one() {
  gpu="$1"; system="$2"; tag="$3"; model="$4"
  wait_gpu "$gpu"
  log "EVAL ${system} -> ${tag} GPU${gpu}"
  CUDA_VISIBLE_DEVICES="$gpu" "$PY" "$CODE/diagnostic_eval.py" \
    --system "$system" --base "$model" --tokenizer "$TOKENIZER" --tag "$tag" \
    --forget-file "$FORGET" --forget-task-id 1 \
    --n-forget 400 --n-retain 400 \
    --strategies DefaultCoT,LessThink,ZeroThink,SummaryThink \
    --max-new-tokens 512 --batch-size 8 > "$LOG/${tag}.eval.log" 2>&1 || true
  "$PY" "$CODE/llm_judge.py" --tags "$tag" --limit-per-group 0 \
    --concurrency 5 --timeout 180 --max-retries 2 --retry-failed \
    > "$LOG/${tag}.judge.log" 2>&1 || true
  (cd "$ROOT/diagnostics" && "$PY" summarize_diagnostic.py \
    --method "$tag" --tag "$tag") > "$LOG/${tag}.summary.log" 2>&1 || true
  log "DONE ${tag}"
  echo -e "${tag}\tDONE" >> "$LOG/status.tsv"
}

: > "$LOG/status.tsv"
# Two GPUs for the first two coefficients.
run_one 0 r2mu01 r2muFull01 "$CKPT/r2mu-forget01/checkpoint-last" & W0=$!
run_one 1 r2mu05 r2muFull05 "$CKPT/r2mu-forget05/checkpoint-last" & W1=$!
wait "$W0" "$W1"
# Third coefficient after the first pair; GPU0 is free.
run_one 0 r2mu10 r2muFull10 "$CKPT/r2mu-forget10/checkpoint-last"

"$PY" - "$ROOT" <<'PY'
import json, sys
from pathlib import Path
root=Path(sys.argv[1])
rows=[]
for name,label in [('r2muFull01','r2mu-0.1'),('r2muFull05','r2mu-0.5'),('r2muFull10','r2mu-1.0')]:
    ep=root/'results'/f'eval_{name}.summary.json'
    jp=root/'results'/f'judge_{name}.summary.json'
    if not ep.exists(): rows.append([label,'MISSING',None,None,None,None]); continue
    ev=json.loads(ep.read_text())
    entity=[g.get('forget',{}).get('leak_rate') for g in ev.get('groups',{}).values() if 'forget' in g]
    retain=[g.get('retain',{}).get('rouge_mean') for g in ev.get('groups',{}).values()]
    retain=[x for x in retain if x is not None]
    hy4=None; cov=None
    if jp.exists():
        jd=json.loads(jp.read_text())
        rates=[g.get('llm_leak_rate') for k,g in jd.get('groups',{}).items()
               if not str(k).endswith(':retain') and g.get('llm_leak_rate') is not None]
        hy4=max(rates) if rates else None
        judged=sum(g.get('judged',0) for g in jd.get('groups',{}).values())
        n=sum(g.get('n',0) for g in jd.get('groups',{}).values())
        cov=judged/n if n else None
    rows.append([label,'DONE',max(entity) if entity else None,hy4,cov,
                 sum(retain)/len(retain) if retain else None])
out=root/'diagnostics'/'R2MU_FULL_TABLE.md'
lines=['# R2MU Full Re-evaluation','',f'Protocol: 400 forget + 400 retain, 4 strategies, 512 tokens, Hy4.','',
       '| Method | Status | max entity leak | max Hy4 leak | Hy4 coverage | retain ROUGE-L |',
       '|---|---|---:|---:|---:|---:|']
for r in rows:
    def f(x): return 'NA' if x is None else f'{x:.4f}'
    lines.append(f'| {r[0]} | {r[1]} | {f(r[2])} | {f(r[3])} | {f(r[4])} | {f(r[5])} |')
lines += ['','Non-claim diagnostic only; no ARIS gate, no claim.']
out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('\n'.join(lines))
PY
log "R2MU full re-evaluation done"
touch "$LOG/R2MU_FULL_DONE"
