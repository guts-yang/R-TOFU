# v1 / v2 Comparison

**Status**: v1 frozen; v2 training/eval in progress. v2 values are not final until
the v2 queue and four-strategy evaluation finish.

## v1 (frozen)

Source: `FULL_EVAL_TABLE_v1.md`.

| Method | Status | max entity leak | Γ | max Hy4 leak | Hy4 coverage | retain ROUGE-L |
|---|---|---:|---:|---:|---:|---:|
| csda | DONE | 0.6450 | 0.1625 | 0.7462 | 0.9944 | 0.4147 |
| eas | DONE | 0.7075 | 0.2700 | 0.7895 | 0.9969 | 0.4651 |
| rrbu | NO_EVAL | NA | NA | NA | NA | NA |
| disco | NO_EVAL | NA | NA | NA | NA | NA |
| ortho | DONE | 0.7300 | 0.2025 | 0.8161 | 0.9875 | 0.5047 |
| scope | DONE | 0.8200 | 0.0800 | 0.8950 | 0.9956 | 0.5469 |
| sequ | DONE | 0.7050 | 0.1825 | 0.8121 | 0.7681 | 0.4301 |
| cfa | DONE | 0.7200 | 0.2800 | 0.7970 | 0.9900 | 0.5032 |
| ripple | NO_EVAL | NA | NA | NA | NA | NA |
| bound | COLLAPSE | 0.0000 | 0.0000 | 0.0000 | 0.4062 | 0.0027 |

## v2 changes

- Safe-CoT supervision from `reasoned_idk_forget10.json`; question-keyed join.
- Four-strategy training and last-token consistency KL.
- Dev split (40 forget) and early-stop/best-adapter selection.
- `LOW_COVERAGE` / `COLLAPSE` statuses; judge retry-failed.
- v2 run ids `v2_<method>`; v2 eval tags `v2Eval_<method>`.

## v2 values

Pending. Do not fill this table by copying v1 values.

Planned source:

```text
results/eval_v2Eval_<method>.summary.json
results/judge_v2Eval_<method>.summary.json
diagnostics/FULL_EVAL_TABLE_v2.md
```

## Interpretation rule

- v1 remains the only complete comparison for the seven evaluated methods.
- v2 is a new recipe, not a correction of v1.
- A v2 method is not successful unless max Hy4 leak <= 0.25, coverage >= 0.90,
  and retain ROUGE-L >= its v1 value.
- `LOW_COVERAGE` results are excluded from the main ranking.
- `COLLAPSE` is not a success.
