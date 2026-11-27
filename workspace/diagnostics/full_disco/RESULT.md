# full_disco — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `fullEval_disco`  
**Timestamp**: 2026-11-27T04:16:48Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_disco/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.8075 |
| max Hy4 leak | 0.884712 |
| Hy4 coverage | 0.9988 |
| Hy4/entity agreement | 0.9268 |
| mean retain ROUGE-L | 0.4997 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.8075 | 0.877193 | 399/1 | 0.932331 |
| LessThink | 0.8025 | 0.884712 | 399/1 | 0.919799 |
| SummaryThink | 0.7675 | 0.845 | 400/0 | 0.9225 |
| ZeroThink | 0.805 | 0.8725 | 400/0 | 0.9325 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
