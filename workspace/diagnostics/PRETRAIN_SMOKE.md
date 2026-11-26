# Pre-Training Integration Smoke

**Date**: 2026-11-26  
**Scope**: pre-training integration checks only; no convergence run and no claim.

## What was completed

1. All ten ideas have decoupled core implementations under
   `redact/workspace/implementations/`.
2. Full training hooks exist for all ten methods under
   `redact/workspace/implementations/hooks/`:
   CSDA, RRBU, CFA, RIPPLE, EAS, DISCO, ORTHO, SCOPE, SEQU, BOUND.
3. `diagnostic_train_hooked.py` now supports:
   - full hooks for all ten methods
   - multi-step optimizer loop
   - gradient accumulation
   - adapter resume via `--resume`
   - optional reference model for RIPPLE
   - adapter + machine-readable summary output
4. Unit tests: 10 core + 17 hook tests pass.
5. `compileall` and IDE diagnostics: clean.

## 8B smoke results

All runs use `lr=1e-5`, `max_len=128`, seed 1001, one optimizer step unless noted.

| Hook | Sample | Loss | Time | Notes |
|---|---|---:|---:|---|
| CSDA | 1 forget + 1 retain | 128.47 | 2.1 s | real layer patching + diagonal retain covariance |
| EAS | 1 forget + 1 retain | 8.82 | 1.5 s | claim-graph kappa + CoT depth + alpha |
| RRBU | 2 forget + 1 retain | 9.99 | 4.2 s | `functional_call`, 2 inner relearning steps, eager attention |
| DISCO | 1 forget + 1 retain | 2.53 | 2.5 s | 4 policy logits + bare prompt |
| ORTHO | 1 forget + 1 retain | 16.45 | 1.1 s | per-layer subspace bank + drift loss |
| SCOPE | 1 forget + 1 retain | 2.47 | 1.3 s | step logits + scope loss |
| SEQU | 1 forget + 1 retain | 14.23 | 1.8 s | first sequential step + adaptive anchor |
| CFA | 2 forget + 1 retain | 14.08 | 1.4 s | GRL loss + adversary update |
| RIPPLE | 2 forget + 1 retain | 11.76 | 1.3 s | reference model + 408-entity claims graph |
| BOUND | 1 forget + 1 retain | 17.10 | 1.4 s | 4 budgets + censoring evaluator |
| CFA multi-step | 2 forget + 1 retain, grad_accum=2 | 14.08 → 12.98 | 1.9 s | multi-step loop works |
| CFA resume | load prior adapter | 13.98 | 1.4 s | `--resume` works |

RRBU note: the model is loaded with `attn_implementation="eager"` because
`functional_call` backprop through the SDPA efficient-attention kernel is not
implemented in this stack. This is a correctness-preserving but slower path.

## Method-specific eval hooks

- CSDA: step-wise ROUGE-L/cosine and intervention sparsity.
- RRBU: generic `RR(K)` curve and recovery rate.
- CFA: linear / MLP / n-gram SCA auditor.
- RIPPLE: RippleBench-style MCQ accuracy + multi-hop reconstruction rate.

## Commands

```bash
cd /usr/local/workspace/R-TOFU/workspace/code
PYTHONPATH=. /jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python \
  diagnostic_train_hooked.py --method csda --steps 1 --n-forget 1 --n-retain 1 \
  --max-len 128 --lr 1e-5 --run-id pretrain_smoke_csda
# analogous runs for all ten methods
```

## Artifacts

Adapters and summaries are under `workspace/results/pretrain_smoke_*`.
Adapters stay under `results/` and are not committed. Each run wrote
`train_summary.json` and `train_args.json`.

## Remaining before full-data run

- Add exact optimizer/scheduler state checkpoint if exact resume is required
  (the current `--resume` restores adapter weights only).
- Run one full-data 1-epoch pilot, then calibrate the step range and GPU budget.
- Full-data evaluation and Hy4 judging are still ahead.
- Some hooks still use clearly-labelled approximations: ORTHO base drift is
  same-pass, RIPPLE neighbours are the retain batch, SEQU runs the first stream
  step, and BOUND reuses one logits tensor across budgets.

## Boundary

These are integration smokes, not convergence results. No ARIS gate was
advanced, no claim artifact was created, and no result here should be read as
evidence that any method works.
