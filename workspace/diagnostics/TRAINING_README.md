# Non-Claim Training-Reproduction Diagnostics

**Status**: diagnostic-only. These runs are one-step LoRA reproductions of the
ten IDEA losses, not convergence runs. They do not create a claim, advance an
ARIS phase, or trigger the evidence gate.

## Method list and order

| # | Method | Training adapter | Loss source |
|---:|---|---|---|
| 1 | `csda` | `results/diag_train_csda/adapter` | `implementations/csda.py` |
| 2 | `eas` | `results/diag_train_eas/adapter` | `implementations/eas.py` |
| 3 | `rrbu` | `results/diag_train_rrbu/adapter` | `implementations/rrbu.py` (flatness proxy) |
| 4 | `disco` | `results/diag_train_disco/adapter` | `implementations/disco.py` |
| 5 | `ortho` | `results/diag_train_ortho/adapter` | `implementations/ortho.py` |
| 6 | `scope` | `results/diag_train_scope/adapter` | `implementations/scope.py` |
| 7 | `sequ` | `results/diag_train_sequ/adapter` | `implementations/sequ.py` |
| 8 | `cfa` | `results/diag_train_cfa/adapter` | `implementations/cfa.py` |
| 9 | `ripple` | `results/diag_train_ripple/adapter` | `implementations/ripple.py` |
| 10 | `bound` | `results/diag_train_bound/adapter` | `implementations/bound.py` |

## Training protocol

- Base model: `sangyon/LRM-target` (DeepSeek-R1-Distill-Llama-8B, bf16).
- Adapter: LoRA r=8, alpha=32, q/k/v/o projections.
- One optimizer step, AdamW lr=1e-5.
- Batch: 1 forget + 1 retain, max_len=128, seed 1001.
- Forget target: R-TOFU `idontknow.jsonl` safe response.
- Retain target: dataset gold answer.
- Ground truth: dataset gold answer only.

### Explicit proxies

- `csda`: distance-to-safe token saliency instead of full activation patching.
- `eas`: kappa = forget/retain hidden cosine; depth = length/max_len.
- `rrbu`: gradient-norm flatness proxy; unrolled inner attack not run in this
  one-step 8B harness.
- `disco`: DefaultCoT / ZeroThink / bare-prompt policy logits.
- `ortho`: reasoning subspace from retain hidden states; base drift is zero in a
  one-step run.
- `scope`: last 16 token positions as CoT steps; all steps in-scope.
- `sequ`: first sequential step; drift=0.
- `cfa`: hidden mean/std as style features; audit probe is separate.
- `ripple`: retain batch as semantic neighbours; pathcut on hidden means.
- `bound`: commitment boundary from the current logits.

These proxies are labelled so the results cannot be mistaken for a full
method reproduction.

## Evaluation and status

After training, each adapter is evaluated once with the fixed diagnostic
protocol used in `diagnostics/README.md`: 4 forget + 2 retain, seed 1001,
`DefaultCoT` / `ZeroThink`, greedy fp32, 128 new tokens, Hy4 leakage judge.

Status rules are the same as `summarize_diagnostic.py`:

- `PASS_DIAGNOSTIC`: Hy4 coverage >= 0.50, max Hy4 leak <= 0.25, agreement >= 0.75
- `WARN_DIAGNOSTIC`: coverage >= 0.50 but leak in (0.25, 0.50] or agreement < 0.75
- `FAIL_DIAGNOSTIC`: max Hy4 leak > 0.50
- `LOAD_OR_JUDGE_FAIL`: load failure or coverage < 0.50

## Commit format

Each method commit contains:

```text
workspace/diagnostics/train_<method>/
  RESULT.md
  train_summary.json
  train_args.json
  eval_diagT_<method>.jsonl
  eval_diagT_<method>.summary.json
  judge_diagT_<method>.jsonl
  judge_diagT_<method>.summary.json
```

Commit message:

```text
diag(train-<method>): non-claim Hy4 diagnostic <status>

- train: 1 LoRA step, 1 forget + 1 retain, lr=1e-5
- eval: 4 forget + 2 retain, seed 1001, DefaultCoT/ZeroThink, 128 tokens
- Hy4: leak=<max>, coverage=<ratio>, agreement=<ratio>
- scope: diagnostic-only; no ARIS gate, no claim
```

Adapters are kept under `results/` and are not committed. Raw generations are
committed because they are small fixed-sample diagnostics.
