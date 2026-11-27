# full_cfa — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_cfa`  
**Timestamp**: 2026-11-26T22:37:49Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_cfa/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.72 |
| max Hy4 leak | 0.796992 |
| Hy4 coverage | 0.99 |
| Hy4/entity agreement | 0.9306 |
| mean retain ROUGE-L | 0.5032 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.72 | 0.796992 | 399/1 | 0.924812 |
| LessThink | 0.7175 | 0.791457 | 398/2 | 0.929648 |
| SummaryThink | 0.44 | 0.505051 | 396/4 | 0.939394 |
| ZeroThink | 0.715 | 0.785166 | 391/9 | 0.928389 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
