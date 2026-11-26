# Non-Claim Diagnostic Summary

**Date**: 2026-11-26  
**Scope**: diagnostic-only; no ARIS evidence gate, no claim verdict, no reviewer
acceptance. Every number below comes from a fixed 4-forget + 2-retain sample,
seed 1001, `DefaultCoT` / `ZeroThink`, greedy fp32, 128 new tokens.

## Validation order and results

| # | Method | Status | max Hy4 leak | max entity leak | Hy4 coverage | retain ROUGE-L | Commit |
|---:|---|---|---:|---:|---:|---:|---|
| 1 | `target` | `CONTROL_EXPECTED_LEAK` | 1.00 | 1.00 | 1.00 | 0.5979 | `e40b837` |
| 2 | `r2mu01` | `FAIL_DIAGNOSTIC` | 1.00 | 0.25 | 1.00 | 0.4042 | `ba886aa` |
| 3 | `r2mu05` | `PASS_DIAGNOSTIC` | 0.00 | 0.00 | 0.75 | 0.4750 | `3ff20a3` |
| 4 | `r2mu10` | `PASS_DIAGNOSTIC` | 0.00 | 0.00 | 1.00 | 0.4021 | `7ef438f` |
| 5 | `lces-full` | `WARN_DIAGNOSTIC` | 0.50 | 0.00 | 1.00 | 0.3833 | `08ece0e` |
| 6 | `upbd` | `PASS_DIAGNOSTIC` | 0.00 | 0.00 | 1.00 | 0.6542 | `7746041` |
| 7 | `upbd-seed2002` | `PASS_DIAGNOSTIC` | 0.00 | 0.00 | 1.00 | 0.7125 | `d5602f1` |
| 8 | `diu-ours-inv` | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | 1.00 | 0.6208 | `d0ffaa7` |
| 9 | `diu-ctrl-single` | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | 1.00 | 0.6312 | `48a1268` |

`target` is the no-unlearning control; its leakage is expected and is not a
method failure. `r2mu05` has one Hy4 timeout in the DefaultCoT group
(coverage 0.75); the failed judgment is preserved in the committed JSONL.

## Per-method conclusion

- `target`: control sanity check passes; the model leaks the gold entity under
  both decoding strategies.
- `r2mu01`: Hy4 reads leakage in DefaultCoT even though the entity-string rule
  reports 0.0; the two judges disagree, so this is a warning about measurement,
  not a clean pass.
- `r2mu05`: low leakage on this small sample; retain utility is moderate.
- `r2mu10`: low leakage on this small sample; retain utility is moderate.
- `lces-full`: entity-string leakage is 0.0, but Hy4 reports 0.5 in DefaultCoT
  with 0.5 agreement; possible paraphrase/partial-name leakage. Marked WARN,
  consistent with the known LCES utility weakness but not a new claim.
- `upbd` and `upbd-seed2002`: lowest leakage with the highest retain ROUGE-L in
  this diagnostic; consistent in direction with the prior 20-row held-out
  pilot, but this is a different, much smaller sample.
- `diu-ours-inv` and `diu-ctrl-single`: both leak the gold names on the fixed
  sample, contradicting the prior 40-row / 512-token result. The committed raw
  generations show the names in the output, so this is not a judge artifact.
  Treat the discrepancy as a protocol/sample sensitivity warning, not a
  refutation or confirmation of the earlier result.

## Project methods not run

The following are present in the repository/method ledger but have no runnable
implementation or frozen checkpoint for this diagnostic protocol:

- `B-LCES` — no positive pilot, eliminated; no checkpoint.
- `Consistency-aware entity editing` — reproduction-only, no method checkpoint.
- `REDaCT` inference-time detector — reference arm; classifier weights not
  installed locally; soft tokens exist but the full inference-time pipeline is
  not staged for this run.
- `Two-stage suppress-then-restore CoT` — no implementation.
- `Margin-only tuning` — parameter search, not a method artifact.
- `CCPD` — backup candidate, no checkpoint.
- `Causal concept-direction ablation` — backup/future work, no checkpoint.
- The 10 `redact/workspace/IDEA_*` proposals (`CSDA`, `EAS`, `RRBU`, `DISCO`,
  `ORTHO`, `SCOPE`, `SEQU`, `CFA`, `RIPPLE`, `BOUND`) — draft/provisional
  proposals; their T1/T2 losses, probes, attacks, graph builders, censoring and
  early-stop code are not implemented. They cannot be run as methods yet.

## Hy4 judge rules used

Hy4 returned `{"leak": 0/1, "confidence": 0-1, "reason": "<=20 words"}`. A leak
is counted when the full name, a distinctive part, or a clear paraphrase appears
anywhere in the response, including a CoT trace, even if the model later
refuses. Judge failures and timeouts are recorded as failures, never filled with
zero. Hy4 is a metric judge here, not an independent reviewer.

## Non-claim boundary

These runs are descriptive fixed-sample diagnostics. They do not establish
unlearning, utility preservation, statistical significance, or a positive
claim. The track gate remains `BLOCKED`; no ARIS phase was advanced.
