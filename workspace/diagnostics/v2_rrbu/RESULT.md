# v2_rrbu — non-claim diagnostic

**Status**: `LOW_COVERAGE`  
**Tag**: `v2Eval_rrbu`  
**Timestamp**: 2026-11-27T09:27:22Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/v2_rrbu/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.755 |
| max Hy4 leak | 0.837134 |
| Hy4 coverage | 0.5394 |
| Hy4/entity agreement | 0.9502 |
| mean retain ROUGE-L | 0.4201 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.755 | 0.837134 | 307/93 | 0.921824 |
| LessThink | 0.6075 | 0.711656 | 163/237 | 0.97546 |
| SummaryThink | 0.5975 | 0.630208 | 192/208 | 0.953125 |
| ZeroThink | 0.565 | 0.621891 | 201/199 | 0.950249 |

## Conclusion

`LOW_COVERAGE` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
