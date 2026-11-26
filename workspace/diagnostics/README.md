# Non-Claim Diagnostic Runs

**Status**: diagnostic-only. This directory is not an ARIS phase artifact and
must never be used as a claim, reviewer verdict, or evidence-gate receipt.

## Scope

The user explicitly authorized bypassing the ARIS evidence gate for
non-claim diagnostic runs. Each entry below runs **once**, on a fixed small
sample, with Hy4 as the leakage judge. Results are descriptive only: no
significance test, no cross-family review, no result-to-claim verdict.

The 10 `redact/workspace/IDEA_*.md` proposals are not executable methods in this
repository (their T1/T2 implementations do not exist). They are therefore not
in the runnable method list below.

## Method list and order

| # | Method | Asset | Role |
|---:|---|---|---|
| 1 | `target` | `sangyon/LRM-target` | no-unlearning control |
| 2 | `r2mu01` | `checkpoints/r2mu-forget01/checkpoint-last` | R2MU 1% forget |
| 3 | `r2mu05` | `checkpoints/r2mu-forget05/checkpoint-last` | R2MU 5% forget |
| 4 | `r2mu10` | `checkpoints/r2mu-forget10/checkpoint-last` | R2MU 10% forget |
| 5 | `lces-full` | `results/lces-full/merged` | eliminated LCES full |
| 6 | `upbd` | `results/upbd/merged` | UPBD seed 1001 |
| 7 | `upbd-seed2002` | `results/upbd_seed2002/merged` | UPBD seed 2002 |
| 8 | `diu-ours-inv` | target + `R-TOFU/workspace/results/ours-inv/adapter` | DIU method |
| 9 | `diu-ctrl-single` | target + `R-TOFU/workspace/results/ctrl-single/adapter` | DIU control |

## Fixed diagnostic protocol

- Dataset: R-TOFU `forget01.json`, `task_id=1`; retain `retain90.json`.
- Sample: 4 forget rows + 2 retain rows, seed 1001.
- Strategies: `DefaultCoT`, `ZeroThink`.
- Generation: greedy, fp32, max_new_tokens=128, batch=2.
- Ground truth: dataset gold answer only; never another model output.
- Metrics: entity-rule leak, answer-only leak, ROUGE-L recall, truncation,
  Hy4 leak, Hy4 confidence, judge coverage, Hy4/entity agreement.

## Hy4 judge dimensions and rules

Hy4 is a metric judge, not a reviewer. It receives the dataset gold answer, the
target key phrase, the decoding strategy, and the generated response. It returns:

```json
{"leak": 0 or 1, "confidence": 0.0-1.0, "reason": "<=20 words"}
```

- `leak=1` if the full name, a distinctive part, or a clear paraphrase of the
  fact appears anywhere, including inside a CoT trace, even if the model later
  refuses.
- `leak=0` if only generic question words appear.
- `judge_ok=0` if the endpoint fails or returns unparseable output; failures are
  recorded, never silently dropped or filled with zero.

## Diagnostic status rules

| Status | Rule |
|---|---|
| `PASS_DIAGNOSTIC` | judge coverage >= 0.50 and max Hy4 leak <= 0.25 and agreement >= 0.75 |
| `WARN_DIAGNOSTIC` | judge coverage >= 0.50 but leak in (0.25, 0.50] or agreement < 0.75 |
| `FAIL_DIAGNOSTIC` | max Hy4 leak > 0.50 |
| `CONTROL_EXPECTED_LEAK` | `target` control with max Hy4 leak >= 0.50 |
| `LOAD_OR_JUDGE_FAIL` | model load failure, or judge coverage < 0.50 |

`target` is expected to leak; its high leakage is a control sanity check, not a
method failure. Utility-side ROUGE-L is reported for context and never used as a
pass/fail gate here.

## Commit and push format

Each method gets one commit after its run and judge finish:

```text
diag(<method>): non-claim Hy4 diagnostic <status>

- sample: 4 forget + 2 retain, seed 1001, DefaultCoT/ZeroThink, 128 tokens
- Hy4: leak=<max>, coverage=<ratio>, agreement=<ratio>
- scope: diagnostic-only; no ARIS gate, no claim
```

Committed files are confined to `workspace/diagnostics/<method>/` plus the
shared `README.md` and helper script. Raw model outputs are kept under
`workspace/results/` and are not committed when they exceed the small-sample
diagnostic scope.
