# One-Step Training-Reproduction Diagnostic Summary

**Date**: 2026-11-26  
**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.

## Protocol

- Base: `sangyon/LRM-target`, LoRA r=8 / alpha=32 on q,k,v,o.
- Training: 1 optimizer step, AdamW lr=1e-5, 1 forget + 1 retain, max_len=128,
  seed 1001, forget target = `idontknow.jsonl`, retain target = gold answer.
- Evaluation: 4 forget + 2 retain, seed 1001, `DefaultCoT` / `ZeroThink`, greedy
  fp32, 128 new tokens, Hy4 leakage judge with 2 judged rows per policy.

This is deliberately a **one-step** diagnostic, not a convergence run. It tests
whether the method's training path executes and whether a single update moves
the fixed-sample leakage readout. It does not validate the method's eventual
utility/unlearning tradeoff.

## Results

| # | Method | Training loss | Status | max Hy4 leak | max entity leak | Commit |
|---:|---|---:|---|---:|---:|---|
| 1 | `csda` | 1,212,418.5 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `50108be` |
| 2 | `eas` | 8.93 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `13dae13` |
| 3 | `rrbu` | 135.29 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `6f99cef` |
| 4 | `disco` | 2.53 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `96029e1` |
| 5 | `ortho` | 16.45 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `6d54387` |
| 6 | `scope` | 2.47 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `2313c33` |
| 7 | `sequ` | 14.23 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `900232e` |
| 8 | `cfa` | 16.33 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `c1f86db` |
| 9 | `ripple` | 14.23 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `eebe647` |
| 10 | `bound` | 16.61 | `FAIL_DIAGNOSTIC` | 1.00 | 1.00 | `90bfa92` |

The exact loss should be read from each `train_<method>/train_summary.json`; the
table is a convenience view. All ten adapters still leak the gold entity on the
fixed sample after one step.

## Conclusion

Under this minimal one-step protocol, **none of the ten methods reproduces
unlearning**: all ten adapters remain at max Hy4 leak = 1.00 and max entity
leak = 1.00. This is a negative diagnostic result for the one-step training
path, not evidence that the methods are invalid. One step on one forget/retain
pair is far below the budget needed for any convergence claim, and several
methods use explicit first-order proxies:

- `csda`: distance-to-safe token saliency, not full activation patching.
- `rrbu`: gradient-norm flatness proxy, not unrolled inner attack.
- `disco`: three policy logits, no multi-step min-max optimization.
- `ortho`: subspace drift is zero in a one-step run because the reference is the
  same forward pass.
- `cfa`: hidden mean/std as style features, not generated-response styles.
- `ripple`: retain batch as neighbours, no knowledge-graph multi-hop set.
- `sequ`: first sequential step only; drift = 0.

A real reproduction needs per-method multi-step training, larger forget/retain
batches, and the method-specific hooks (activation patching, unrolled attack,
knowledge graph, generated style features, sequential state). Until then, the
only defensible statement is: the decoupled training paths execute and save
adapters, but one step does not move the leakage readout.

## Commits

Infrastructure: `5100945 chore(diagnostics): add one-step non-claim training harness`.

Per-method commits are listed in the table above. All were pushed to
`guts-yang/R-TOFU` on branch `Auto`. Adapters remain under `workspace/results/`
and are not committed; each result directory contains `RESULT.md`,
`train_summary.json`, `train_args.json`, and the eval/judge JSON files.

## Non-claim boundary

No ARIS phase was advanced, no `run_state.py accept` was called, and no claim
artifact was created. These are descriptive one-step diagnostics only.
