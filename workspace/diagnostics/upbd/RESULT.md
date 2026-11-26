# upbd — non-claim diagnostic

**Status**: `PASS_DIAGNOSTIC`  
**Tag**: `diag_upbd`  
**Timestamp**: 2026-11-26T13:09:38Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 4 forget + 2 retain, seed 1001
- Strategies: DefaultCoT, ZeroThink
- Max new tokens: 128; dtype: fp32
- Base: `/jizhicfs/chenyliao/lrm-unlearning/results/upbd/merged`
- Adapter: `None`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.0 |
| max Hy4 leak | 0.0 |
| Hy4 coverage | 1.0 |
| Hy4/entity agreement | 1.0 |
| mean retain ROUGE-L | 0.6542 |
| generation rows | 12 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.0 | 0.0 | 2/0 | 1.0 |
| ZeroThink | 0.0 | 0.0 | 2/0 | 1.0 |

## Conclusion

`PASS_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
