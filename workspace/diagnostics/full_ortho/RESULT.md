# full_ortho — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_ortho`  
**Timestamp**: 2026-11-26T22:26:52Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_ortho/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.73 |
| max Hy4 leak | 0.816121 |
| Hy4 coverage | 0.9875 |
| Hy4/entity agreement | 0.9266 |
| mean retain ROUGE-L | 0.5047 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.72 | 0.798489 | 397/3 | 0.926952 |
| LessThink | 0.73 | 0.816121 | 397/3 | 0.919395 |
| SummaryThink | 0.5275 | 0.596491 | 399/1 | 0.932331 |
| ZeroThink | 0.715 | 0.788114 | 387/13 | 0.927649 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
