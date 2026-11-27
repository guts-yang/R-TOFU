#!/usr/bin/env bash
# Read-only watcher: as each Hy4 judge finishes, write that method's RESULT.md
# and append a compact partial-results row. It never touches running judges.
set -uo pipefail
ROOT=/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace
CODE="$ROOT/code"
DIAG="$ROOT/diagnostics"
LOG="$ROOT/logs/v2_results"
PY=/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python
mkdir -p "$LOG"
METHODS=(eas csda scope rrbu cfa disco ortho sequ ripple bound)
PARTIAL="$DIAG/V2_PARTIAL_RESULTS.tsv"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG/watcher.log"; }

[ -f "$PARTIAL" ] || printf 'method\ttag\tmax_entity_leak\tmax_hy4_leak\tcoverage\tretain_rouge\tstatus\twritten_at\n' > "$PARTIAL"

while true; do
  for m in "${METHODS[@]}"; do
    tag="v2Eval_${m}"
    ev="$ROOT/results/eval_${tag}.summary.json"
    jd="$ROOT/results/judge_${tag}.summary.json"
    out="$DIAG/v2_${m}/RESULT.md"
    [ -f "$ev" ] || continue
    [ -f "$jd" ] || continue
    if [ -f "$out" ] && [ "$out" -nt "$jd" ]; then
      continue
    fi
    log "write result ${m}"
    (cd "$DIAG" && "$PY" summarize_diagnostic.py \
      --method "v2_${m}" --tag "$tag") > "$LOG/${m}.summary.log" 2>&1 || true
    if [ -f "$out" ]; then
      "$PY" - "$m" "$tag" "$ev" "$jd" "$PARTIAL" <<'PY'
import json, sys
from datetime import datetime, timezone
m, tag, evp, jdp, outp = sys.argv[1:]
ev = json.load(open(evp, encoding='utf-8'))
jd = json.load(open(jdp, encoding='utf-8'))
entity = [g.get('forget', {}).get('leak_rate') for g in ev.get('groups', {}).values()
          if 'forget' in g]
hy4 = [g.get('llm_leak_rate') for k, g in jd.get('groups', {}).items()
       if not str(k).endswith(':retain') and g.get('llm_leak_rate') is not None]
judged = sum(v.get('judged', 0) for v in jd.get('groups', {}).values())
n = sum(v.get('n', 0) for v in jd.get('groups', {}).values())
retain = [g.get('retain', {}).get('rouge_mean') for g in ev.get('groups', {}).values()]
retain = [x for x in retain if x is not None]
row = [m, tag,
       '' if not entity else f'{max(entity):.4f}',
       '' if not hy4 else f'{max(hy4):.4f}',
       f'{judged/n:.4f}' if n else '',
       f'{sum(retain)/len(retain):.4f}' if retain else '',
       'WRITTEN',
       datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')]
with open(outp, 'a', encoding='utf-8') as f:
    f.write('\t'.join(row) + '\n')
PY
      log "result written ${m}"
    fi
  done
  [ -f "$ROOT/logs/pair_async/PAIR_ASYNC_DONE" ] && { log "async done"; break; }
  sleep 60
done
log "watcher exit"
