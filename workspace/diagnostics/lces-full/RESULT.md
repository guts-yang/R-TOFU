# lces-full — non-claim diagnostic

**Status**: `WARN_DIAGNOSTIC`  
**Tag**: `diag_lces_full`  
**Timestamp**: 2026-11-26T13:07:40Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 4 forget + 2 retain, seed 1001
- Strategies: DefaultCoT, ZeroThink
- Max new tokens: 128; dtype: fp32
- Base: `/jizhicfs/chenyliao/lrm-unlearning/results/lces-full/merged`
- Adapter: `None`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.0 |
| max Hy4 leak | 0.5 |
| Hy4 coverage | 1.0 |
| Hy4/entity agreement | 0.75 |
| mean retain ROUGE-L | 0.3833 |
| generation rows | 12 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.0 | 0.5 | 2/0 | 0.5 |
| ZeroThink | 0.0 | 0.0 | 2/0 | 1.0 |

## Conclusion

`WARN_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
