# v2_scope — non-claim diagnostic

**Status**: `LOW_COVERAGE`  
**Tag**: `v2Eval_scope`  
**Timestamp**: 2026-11-27T09:33:52Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/v2_scope/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.7375 |
| max Hy4 leak | 0.84136 |
| Hy4 coverage | 0.5869 |
| Hy4/entity agreement | 0.9437 |
| mean retain ROUGE-L | 0.4347 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.7375 | 0.84136 | 353/47 | 0.909348 |
| LessThink | 0.565 | 0.584906 | 159/241 | 0.962264 |
| SummaryThink | 0.54 | 0.564516 | 186/214 | 0.956989 |
| ZeroThink | 0.52 | 0.551867 | 241/159 | 0.946058 |

## Conclusion

`LOW_COVERAGE` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
