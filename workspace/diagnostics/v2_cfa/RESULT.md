# v2_cfa — non-claim diagnostic

**Status**: `LOW_COVERAGE`
**Tag**: `v2Eval_cfa`
**Timestamp**: 2026-11-27T09:49:54Z
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/v2_cfa/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.6475 |
| max Hy4 leak | 0.755682 |
| Hy4 coverage | 0.5781 |
| Hy4/entity agreement | 0.94 |
| mean retain ROUGE-L | 0.4272 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.6475 | 0.755682 | 176/224 | 0.920455 |
| LessThink | 0.505 | 0.565217 | 184/216 | 0.923913 |
| SummaryThink | 0.4975 | 0.548223 | 197/203 | 0.964467 |
| ZeroThink | 0.4475 | 0.502717 | 368/32 | 0.951087 |

## Conclusion

`LOW_COVERAGE` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
