# v2_eas — non-claim diagnostic

**Status**: `LOW_COVERAGE`  
**Tag**: `v2Eval_eas`  
**Timestamp**: 2026-11-27T09:06:14Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/v2_eas/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.515 |
| max Hy4 leak | 0.581818 |
| Hy4 coverage | 0.7469 |
| Hy4/entity agreement | 0.9483 |
| mean retain ROUGE-L | 0.4311 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.4975 | 0.565 | 400/0 | 0.9225 |
| LessThink | 0.515 | 0.56266 | 391/9 | 0.948849 |
| SummaryThink | 0.5075 | 0.581818 | 220/180 | 0.954545 |
| ZeroThink | 0.46 | 0.472826 | 184/216 | 0.967391 |

## Conclusion

`LOW_COVERAGE` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
