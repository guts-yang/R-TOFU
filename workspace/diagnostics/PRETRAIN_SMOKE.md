# Pre-Training Integration Smoke

**Date**: 2026-11-26  
**Scope**: pre-training integration checks only; no convergence run and no claim.

## What was completed

1. Full hooks for CSDA, RRBU, CFA, and RIPPLE are implemented under
   `redact/workspace/implementations/hooks/`.
2. `diagnostic_train_hooked.py` now supports:
   - full hooks for the four methods
   - multi-step optimizer loop
   - gradient accumulation
   - adapter resume via `--resume`
   - optional reference model for RIPPLE
   - adapter + machine-readable summary output
3. The four full hooks were exercised on `sangyon/LRM-target` with LoRA.
4. Unit tests: 10 core + 7 hook tests pass.
5. `compileall` and IDE diagnostics: clean.

## 8B smoke results

All runs use `lr=1e-5`, `max_len=128`, seed 1001, one or two steps.

| Hook | Command summary | Steps | Loss | Time | Notes |
|---|---|---:|---:|---:|---|
| CSDA | 1 forget + 1 retain | 1 | 128.47 | 2.1 s | real layer patching + diagonal retain covariance |
| RRBU | 2 forget + 1 retain | 1 | 9.99 | 4.2 s | `functional_call`, 2 inner relearning steps, eager attention |
| CFA | 2 forget + 1 retain | 1 | 14.08 | 1.4 s | GRL loss + adversary update |
| RIPPLE | 2 forget + 1 retain | 1 | 11.76 | 1.3 s | reference model + 408-entity claims graph |
| CFA multi-step | 2 forget + 1 retain, grad_accum=2 | 2 | 14.08 → 12.98 | 1.9 s | multi-step loop works |
| CFA resume | load prior adapter | 1 | 13.98 | 1.4 s | `--resume` works |

RRBU note: the model is loaded with `attn_implementation="eager"` because
`functional_call` backprop through the SDPA efficient-attention kernel is not
implemented in this stack. This is a correctness-preserving but slower path.

## Commands

```bash
cd /usr/local/workspace/R-TOFU/workspace/code
PYTHONPATH=. /jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python \
  diagnostic_train_hooked.py --method csda --steps 1 --n-forget 1 --n-retain 1 \
  --max-len 128 --lr 1e-5 --run-id pretrain_smoke_csda
# analogous runs for rrbu / cfa / ripple
```

## Artifacts

Adapters and summaries are under:

```text
workspace/results/pretrain_smoke_csda/
workspace/results/pretrain_smoke_rrbu/
workspace/results/pretrain_smoke_cfa/
workspace/results/pretrain_smoke_ripple/
workspace/results/pretrain_smoke_cfa_multi/
workspace/results/pretrain_smoke_resume/
```

Adapters stay under `results/` and are not committed. Each run wrote
`train_summary.json` and `train_args.json`.

## Remaining before full-data run

- Replace the remaining proxy branches (EAS/ORTHO/SCOPE/SEQU/DISCO/BOUND) if
  full-method parity is required; the four hardest hooks are already integrated.
- Add a real optimizer/scheduler state checkpoint if exact resume is required
  (the current `--resume` restores adapter weights only).
- Run one full-data 1-epoch pilot, then calibrate the step range and GPU budget.
- Full-data evaluation and Hy4 judging are still ahead.

## Boundary

These are integration smokes, not convergence results. No ARIS gate was
advanced, no claim artifact was created, and no result here should be read as
evidence that any method works.
