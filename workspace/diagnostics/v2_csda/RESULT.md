# v2_csda — non-claim diagnostic

**Status**: `LOW_COVERAGE`  
**Tag**: `v2Eval_csda`  
**Timestamp**: 2026-11-27T09:19:14Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/v2_csda/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.6525 |
| max Hy4 leak | 0.753181 |
| Hy4 coverage | 0.63 |
| Hy4/entity agreement | 0.9148 |
| mean retain ROUGE-L | 0.339 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.6525 | 0.753181 | 393/7 | 0.89313 |
| LessThink | 0.5475 | 0.624031 | 258/142 | 0.934109 |
| SummaryThink | 0.4875 | 0.570588 | 170/230 | 0.917647 |
| ZeroThink | 0.5875 | 0.652406 | 187/213 | 0.914439 |

## Conclusion

`LOW_COVERAGE` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
