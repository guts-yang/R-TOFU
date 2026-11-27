# full_csda — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_csda`  
**Timestamp**: 2026-11-26T20:51:20Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_csda/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.645 |
| max Hy4 leak | 0.746231 |
| Hy4 coverage | 0.9944 |
| Hy4/entity agreement | 0.8711 |
| mean retain ROUGE-L | 0.4147 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.645 | 0.746231 | 398/2 | 0.90201 |
| LessThink | 0.4825 | 0.652393 | 397/3 | 0.828715 |
| SummaryThink | 0.5425 | 0.681704 | 399/1 | 0.862155 |
| ZeroThink | 0.625 | 0.738035 | 397/3 | 0.891688 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
