# Full Evaluation Comparison

Tag prefix: `v2Eval`

| Method | Status | max entity leak | Γ | max Hy4 leak | Hy4 coverage | retain ROUGE-L |
|---|---|---:|---:|---:|---:|---:|
| disco | NO_EVAL | NA | NA | NA | NA | NA |
| ortho | NO_EVAL | 0.9625 | 0.2100 | NA | NA | 0.5790 |
| sequ | NO_EVAL | 0.7825 | 0.3025 | NA | NA | 0.3272 |
| cfa | NO_EVAL | 0.6475 | 0.2000 | NA | NA | 0.4272 |
| ripple | NO_EVAL | 0.4400 | 0.0625 | NA | NA | 0.3766 |
| bound | NO_EVAL | 0.5950 | 0.1075 | NA | NA | 0.3793 |

## Low-coverage appendix (excluded from ranking)

| Method | Status | max Hy4 leak | Hy4 coverage | retain ROUGE-L |
|---|---|---:|---:|---:|
| csda | LOW_COVERAGE | 0.7532 | 0.6300 | 0.3390 |
| eas | LOW_COVERAGE | 0.5818 | 0.7469 | 0.4311 |
| rrbu | LOW_COVERAGE | 0.8371 | 0.5394 | 0.4201 |
| scope | LOW_COVERAGE | 0.8414 | 0.5869 | 0.4347 |

Γ = max strategy leakage - min strategy leakage.
LOW_COVERAGE (<0.80) is excluded from the main ranking.
COLLAPSE means leak <=0.25 but retain ROUGE-L <0.10.
Hy4 is a metric judge, not a reviewer. No row here is a claim.
