# train_csda — non-claim diagnostic

**Status**: `FAIL_DIAGNOSTIC`  
**Tag**: `diagT_csda`  
**Timestamp**: 2026-11-26T14:23:09Z  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Fixed protocol

- Samples: 4 forget + 2 retain, seed 1001
- Strategies: DefaultCoT, ZeroThink
- Max new tokens: 128; dtype: fp32
- Base: `/jizhicfs/chenyliao/models/sangyon/LRM-target`
- Adapter: `/usr/local/workspace/R-TOFU/workspace/results/diag_train_csda/adapter`

## Metrics

| Metric | Value |
|---|---:|
| max entity-rule leak | 1.0 |
| max Hy4 leak | 1.0 |
| Hy4 coverage | 1.0 |
| Hy4/entity agreement | 1.0 |
| mean retain ROUGE-L | 0.5979 |
| generation rows | 12 |

## Per-strategy detail

| Strategy | entity leak | Hy4 leak | judged/failed | agreement |
|---|---:|---:|---:|---:|
| DefaultCoT | 1.0 | 1.0 | 2/0 | 1.0 |
| ZeroThink | 1.0 | 1.0 | 2/0 | 1.0 |

## Conclusion

`FAIL_DIAGNOSTIC` is a fixed-sample diagnostic label only. It does not establish unlearning, utility preservation, statistical significance, or a claim.
