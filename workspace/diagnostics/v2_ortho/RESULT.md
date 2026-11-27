# v2_ortho — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`
**Tag**: `v2Eval_ortho`
**Timestamp**: 2026-11-27T10:47:38Z
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 400 forget + 400 retain, seed 1001
- Strategies: DefaultCoT, LessThink, ZeroThink, SummaryThink
- Max new tokens: 512; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace/results/v2_ortho/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.9625 |
| max Hy4 leak | 0.94382 |
| Hy4 coverage | 0.8125 |
| Hy4/entity agreement | 0.9171 |
| mean retain ROUGE-L | 0.579 |
| generation rows | 3200 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.9625 | 0.94382 | 356/44 | 0.910112 |
| LessThink | 0.815 | 0.869955 | 223/177 | 0.914798 |
| SummaryThink | 0.7525 | 0.822981 | 322/78 | 0.916149 |
| ZeroThink | 0.805 | 0.879699 | 399/1 | 0.927318 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
