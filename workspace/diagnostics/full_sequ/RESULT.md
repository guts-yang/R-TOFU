# full_sequ — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_sequ`  
**Timestamp**: 2026-11-26T23:37:53Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_sequ/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.705 |
| max Hy4 leak | 0.812081 |
| Hy4 coverage | 0.7681 |
| Hy4/entity agreement | 0.9351 |
| mean retain ROUGE-L | 0.4301 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.705 | 0.812081 | 149/251 | 0.912752 |
| LessThink | 0.68 | 0.742857 | 280/120 | 0.925 |
| SummaryThink | 0.5225 | 0.5775 | 400/0 | 0.945 |
| ZeroThink | 0.55 | 0.5925 | 400/0 | 0.9575 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
