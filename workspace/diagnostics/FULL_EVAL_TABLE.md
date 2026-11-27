# Full Evaluation Comparison

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
| bound | DONE | 0.0000 | 0.0000 | 0.0000 | 0.4062 | 0.0027 |

Γ = max strategy leakage - min strategy leakage.
Hy4 is a metric judge, not a reviewer. No row here is a claim.
