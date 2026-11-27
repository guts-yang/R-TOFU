# full_rrbu — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_rrbu`  
**Timestamp**: 2026-11-27T02:17:24Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_rrbu/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.7225 |
| max Hy4 leak | 0.79 |
| Hy4 coverage | 0.9988 |
| Hy4/entity agreement | 0.9324 |
| mean retain ROUGE-L | 0.5075 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.7225 | 0.79 | 400/0 | 0.9325 |
| LessThink | 0.705 | 0.78 | 400/0 | 0.925 |
| SummaryThink | 0.645 | 0.71 | 400/0 | 0.935 |
| ZeroThink | 0.7225 | 0.788945 | 398/2 | 0.937186 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
