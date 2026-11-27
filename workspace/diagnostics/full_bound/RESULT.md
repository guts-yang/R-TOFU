# full_bound — non-claim diagnostic

**Status**: `LOAD_OR_JUDGE_FAIL`  
**Tag**: `fullEval_bound`  
**Timestamp**: 2026-11-26T22:55:23Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/full_bound/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.0 |
| max Hy4 leak | 0.0 |
| Hy4 coverage | 0.4062 |
| Hy4/entity agreement | 1.0 |
| mean retain ROUGE-L | 0.0027 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.0 | 0.0 | 191/209 | 1.0 |
| LessThink | 0.0 | 0.0 | 145/255 | 1.0 |
| SummaryThink | 0.0 | 0.0 | 146/254 | 1.0 |
| ZeroThink | 0.0 | 0.0 | 168/232 | 1.0 |

## Conclusion

`LOAD_OR_JUDGE_FAIL` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
