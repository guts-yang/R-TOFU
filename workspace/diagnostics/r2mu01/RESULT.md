# r2mu01 — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `diag_r2mu01`  
**Timestamp**: 2026-11-26T12:47:03Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 4 forget + 2 retain, seed 1001
- Strategies: DefaultCoT, ZeroThink
- Max new tokens: 128; dtype: fp32
- Base: `/jizhicfs/chenyliao/checkpoints/r2mu-forget01/checkpoint-last`
- Adapter: `None`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 0.25 |
| max Hy4 leak | 1.0 |
| Hy4 coverage | 1.0 |
| Hy4/entity agreement | 0.5 |
| mean retain ROUGE-L | 0.4042 |
| generation rows | 12 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 0.0 | 1.0 | 2/0 | 0.0 |
| ZeroThink | 0.25 | 0.5 | 2/0 | 1.0 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
