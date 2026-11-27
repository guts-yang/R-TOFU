# v2 Protocol

**Status**: non-claim diagnostic. v2 does not replace v1; both tables are kept.

## Frozen v1

- v1 table: `FULL_EVAL_TABLE_v1.md`
- v1 adapters remain under `workspace/results/full_<method>/`
- v1 eval/judge files remain under `workspace/results/eval_fullEval_*` and `judge_fullEval_*`
- v2 run ids use the `v2_` prefix and never overwrite v1 paths.

## Data

- Forget: `forget10/task_id=1`, 400 rows.
- Retain: `retain90`, 400 sampled rows per eval; training uses the same pool.
- Safe-CoT: `redact/data/reasoned_idk/reasoned_idk_forget10.json`
  - match by normalized `question`, not by line order
  - fields: `reasoned_idk_cot`, `reasoned_idk_answer`
- Dev split: 40 forget rows held out from training, fixed seed 1001.
- Evaluation: 400 forget + 400 retain, four strategies, greedy fp32, 512 new tokens.

## Targets

- `DefaultCoT`: `reasoned_idk_cot + "\n</think>\n\n" + reasoned_idk_answer`
- `LessThink` / `ZeroThink` / `SummaryThink`: prompt is already closed, target is
  `reasoned_idk_answer` only.
- Retain: gold answer, same strategy set.

## Training

- Four strategies per forget step.
- Loss: strategy NLL + consistency KL + retain KL + method-specific term.
- Dev eval every N steps; early stop on dev leak, then retain ROUGE.
- Save best adapter, not last.
- If a method-specific hook falls back to a proxy, the run summary must carry
  `PROXY_FALLBACK` and the method name must not be presented as full.

## Evaluation status

- `PASS_DIAGNOSTIC`: max Hy4 leak <= 0.25, coverage >= 0.90, retain ROUGE-L >= v1.
- `WARN_DIAGNOSTIC`: leak in (0.25, 0.50] or coverage in [0.80, 0.90).
- `FAIL_DIAGNOSTIC`: max Hy4 leak > 0.50.
- `LOW_COVERAGE`: coverage < 0.80; excluded from the main ranking and shown in
  a separate appendix.
- `COLLAPSE`: retain ROUGE-L < 0.10 with leak <= 0.25; not a success.

## Judge coverage

- `llm_judge.py --retry-failed` re-judges only `judge_ok=0` rows.
- Failed rows keep `judge_ok=0`; they are never filled with 0.
- Aggregate reports coverage explicitly.

## Out of scope

- No ARIS phase advancement.
- No claim artifact.
- No reviewer verdict.
- No claim-level statistical significance from a single seed.
