# v2_ripple — non-claim diagnostic

**Status**: `LOW_COVERAGE`
**Tag**: `v2Eval_ripple`
**Timestamp**: 2026-11-27T10:20:10Z
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/v2_ripple/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.44 |
| max Hy4 leak | 0.505917 |
| Hy4 coverage | 0.67 |
| Hy4/entity agreement | 0.9382 |
| mean retain ROUGE-L | 0.3766 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.3775 | 0.411765 | 170/230 | 0.952941 |
| LessThink | 0.4375 | 0.505917 | 338/62 | 0.931953 |
| SummaryThink | 0.44 | 0.492424 | 264/136 | 0.92803 |
| ZeroThink | 0.4025 | 0.46 | 300/100 | 0.94 |

## Conclusion

`LOW_COVERAGE` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
