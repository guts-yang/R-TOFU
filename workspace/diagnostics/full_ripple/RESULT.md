# full_ripple — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_ripple`  
**Timestamp**: 2026-11-27T05:49:54Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_ripple/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.7275 |
| max Hy4 leak | 0.802005 |
| Hy4 coverage | 0.9981 |
| Hy4/entity agreement | 0.9224 |
| mean retain ROUGE-L | 0.5034 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.7175 | 0.802005 | 399/1 | 0.917293 |
| LessThink | 0.715 | 0.8 | 400/0 | 0.91 |
| SummaryThink | 0.6575 | 0.734336 | 399/1 | 0.924812 |
| ZeroThink | 0.7275 | 0.79198 | 399/1 | 0.937343 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
