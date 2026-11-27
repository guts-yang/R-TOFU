# full_eas — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_eas`  
**Timestamp**: 2026-11-26T19:22:00Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_eas/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.7075 |
| max Hy4 leak | 0.789474 |
| Hy4 coverage | 0.9969 |
| Hy4/entity agreement | 0.9304 |
| mean retain ROUGE-L | 0.4651 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.7025 | 0.789474 | 399/1 | 0.914787 |
| LessThink | 0.7075 | 0.7825 | 400/0 | 0.925 |
| SummaryThink | 0.4375 | 0.5025 | 400/0 | 0.935 |
| ZeroThink | 0.68 | 0.739899 | 396/4 | 0.94697 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
