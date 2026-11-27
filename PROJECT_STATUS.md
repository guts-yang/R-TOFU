# LRM Unlearning Project Status

**Last updated**: 2026-11-27T11:10Z  
**Scope**: non-claim diagnostic reproduction. No ARIS gate, no claim, no reviewer verdict.

---

## 1. Executive Snapshot

| Item | Status |
|---|---|
| v1 full evaluation | complete, frozen in `workspace/diagnostics/FULL_EVAL_TABLE_v1.md` |
| v2 training | 9/10 methods complete; DISCO missing |
| v2 Hy4 | 7/10 complete; BOUND/SEQU running; DISCO missing |
| v2 best method | RIPPLE, max Hy4 0.5059, coverage 0.67 |
| v2 pass count | 0 / 10 |
| R2MU full re-eval | running on 2 GPUs |
| Ablation | not started |
| Final v1/v2/R2MU table | not yet complete |

**Bottom line**: v2 is directionally better on EAS/CFA/SCOPE, but no method reaches
`max Hy4 <= 0.25`, `coverage >= 0.90`, and retain not below v1.

---

## 2. v2 Method Status

Protocol: 400 forget + 400 retain, four strategies, 512 tokens, greedy fp32, Hy4.

| Method | Train | Eval | max entity | max Hy4 | coverage | retain ROUGE | Status |
|---|---|---|---:|---:|---:|---:|---|
| EAS | DONE | DONE | 0.5150 | 0.5818 | 0.7469 | 0.4311 | LOW_COVERAGE |
| CSDA | DONE | DONE | 0.6525 | 0.7532 | 0.6300 | 0.3390 | LOW_COVERAGE |
| SCOPE | DONE | DONE | 0.7375 | 0.8414 | 0.5869 | 0.4347 | LOW_COVERAGE |
| RRBU | DONE | DONE | 0.7550 | 0.8371 | 0.5394 | 0.4201 | LOW_COVERAGE |
| CFA | DONE | DONE | 0.6475 | 0.7557 | 0.5781 | 0.4272 | LOW_COVERAGE |
| RIPPLE | DONE | DONE | 0.4400 | 0.5059 | 0.6700 | 0.3766 | LOW_COVERAGE |
| ORTHO | DONE | DONE | 0.9625 | 0.9438 | 0.8125 | 0.5790 | FAIL_DIAGNOSTIC |
| BOUND | DONE | DONE | 0.5950 | pending | pending | 0.3793 | PENDING_HY4 |
| SEQU | DONE | DONE | 0.7825 | pending | pending | 0.3272 | PENDING_HY4 |
| DISCO | FAILED | MISSING | NA | NA | NA | NA | MISSING_ADAPTER |

### v2 partial-result file

```text
workspace/diagnostics/V2_PARTIAL_RESULTS.tsv
```

Currently contains EAS, CSDA, SCOPE, RRBU; CFA/RIPPLE/ORTHO summaries exist in
`workspace/results/` and need the result watcher to append them.

---

## 3. v1 vs v2

| Method | v1 Hy4 | v2 Hy4 | v1 retain | v2 retain | Direction |
|---|---:|---:|---:|---:|---|
| EAS | 0.7895 | 0.5818 | 0.4651 | 0.4311 | leak down, retain down |
| CSDA | 0.7462 | 0.7532 | 0.4147 | 0.3390 | worse |
| SCOPE | 0.8950 | 0.8414 | 0.5469 | 0.4347 | leak down, retain down |
| CFA | 0.7970 | 0.7557 | 0.5032 | 0.4272 | leak down, retain down |
| ORTHO | 0.8161 | 0.9438 | 0.5047 | 0.5790 | leak much worse |
| SEQU | 0.8121 | pending | 0.4301 | 0.3272 | generation worse |
| BOUND | 0.0000 | pending | 0.0027 | 0.3793 | no longer collapse |
| RIPPLE | no v1 full | 0.5059 | NA | 0.3766 | currently best v2 leak |
| RRBU | no v1 full | 0.8371 | NA | 0.4201 | evaluated, low coverage |
| DISCO | no v1 full | missing | NA | NA | failed |

---

## 4. R2MU Full Re-evaluation

Current queue:

```text
r2mu-0.1 + r2mu-0.5 on GPU0/GPU1
r2mu-1.0 after both
```

Previous failure: checkpoint tokenizer was corrupted. Fixed with:

```text
--tokenizer /jizhicfs/chenyliao/models/sangyon/LRM-target
```

Small-sample prior reference (40+20, not comparable to full):

| Method | entity | Hy4 | coverage | retain |
|---|---:|---:|---:|---:|
| R2MU-0.1 | 0.20 | 0.3333 | 0.8438 | 0.3455 |
| R2MU-0.5 | 0.00 | 0.0000 | 1.0000 | 0.3686 |
| R2MU-1.0 | 0.00* | 0.0000* | 1.0000* | 0.4021* |

`*` only 4 forget + 2 retain diagnostic; not full protocol.

Full table will be written to:

```text
workspace/diagnostics/R2MU_FULL_TABLE.md
```

---

## 5. Current GPU / Processes

At last check:

```text
GPU0: 98%, ~31.7 GB -> R2MU-0.1 eval
GPU1: 98%, ~31.7 GB -> R2MU-0.5 eval
```

Background CPU/network:

```text
Hy4: BOUND, SEQU
R2MU: 0.1 / 0.5
```

Key logs:

```text
workspace/logs/pair_async/queue.log
workspace/logs/pair_async/status.tsv
workspace/logs/disco_retry/queue.log
workspace/logs/r2mu_full/queue.log
workspace/logs/v2_results/watcher.log
```

---

## 6. Known Issues

1. **DISCO has no adapter**
   - Full hook: `libcublasLt` SIGFPE around step 128.
   - Proxy fallback: first failed `target too long (285 > 256)`.
   - Proxy with max_len=512 later OOM because another process used ~94.96 GB.
   - Needs another retry after GPU is free.

2. **Coverage is low for most methods**
   - EAS 0.7469, CSDA 0.6300, SCOPE 0.5869, RRBU 0.5394.
   - CFA 0.5781, RIPPLE 0.6700.
   - None reaches 0.90; do not rank them as final.

3. **v2 batch is much smaller than v1**
   - v1 often used 8+8 or 16+16; v2 mostly 2+2.
   - This confounds the v1/v2 comparison.

4. **No ablation yet**
   - `ablation_runner.py` exists; no ablation runs recorded.

5. **R2MU full eval is still running**
   - Do not reuse the old 40+20 numbers as final.

---

## 7. Next Steps

1. Finish R2MU-0.1/0.5/1.0 full evaluation.
2. Finish BOUND/SEQU Hy4.
3. Retry DISCO on an actually free GPU:
   - proxy path preferred;
   - `--max-len 384` or 512 to avoid target-too-long;
   - record `PROXY_FALLBACK` if used.
4. Generate final v2 table and v1/v2 comparison.
5. Start ablation on dev subset:
   - CSDA mask/lambda
   - EAS alpha
   - RRBU K
   - ORTHO k/drift
   - SCOPE mask
   - SEQU delta
   - CFA beta
   - RIPPLE hops
   - BOUND budgets
6. Only then consider full confirmation for methods that show a real gain.

---

## 8. Monitoring Commands

```bash
cd /usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace

# v2 queue
tail -f logs/pair_async/queue.log logs/pair_async/status.tsv

# per-method training
tail -f logs/pair_async/eas.train.log logs/pair_async/scope.train.log

# DISCO repair
tail -f logs/disco_retry/queue.log

# R2MU full eval
tail -f logs/r2mu_full/queue.log

# current GPU
watch -n 10 nvidia-smi
```

---

## 9. Non-Claim Boundary

This dashboard records diagnostic engineering progress only. It is not:

- an unlearning proof,
- a utility preservation proof,
- a statistical significance test,
- an ARIS evidence-gate result,
- a reviewer verdict.
