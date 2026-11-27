# full_scope — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_scope`  
**Timestamp**: 2026-11-26T21:10:18Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_scope/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.82 |
| max Hy4 leak | 0.895 |
| Hy4 coverage | 0.9956 |
| Hy4/entity agreement | 0.9259 |
| mean retain ROUGE-L | 0.5469 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.8075 | 0.88665 | 397/3 | 0.926952 |
| LessThink | 0.81 | 0.889724 | 399/1 | 0.922306 |
| SummaryThink | 0.74 | 0.816121 | 397/3 | 0.929471 |
| ZeroThink | 0.82 | 0.895 | 400/0 | 0.925 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
