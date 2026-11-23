# EXPERIMENT TRACKER

> 状态来自 `logs/full.out`、`logs/eval_ours-inv.out`、`logs/recompute.out`、`logs/judge.out`
> 与 `results/eval_*.summary.json`；数字可追溯到具体结果文件。

| Run ID | Milestone | System | Config | Status | Key Metric | Notes |
|---|---|---|---|---|---|---|
| R000 | M0 | target | sanity, 2 forget + 1 retain, 2 strategies, 64 tokens | DONE | 生成/落盘正常 | 初版 bf16+KV cache 触发 SIGFPE；改用 fp32 / cu124 后通过 |
| R001 | M1 | target | 40 forget + 20 retain, 4 strategies | DONE | Γ=0.050, max ρ=0.050 | 遗忘前对照；生成退化、truncated≈0.95 |
| R002 | M1 | r2mu01 | 同上 | DONE | Γ=0.050, max ρ=0.200 | 主诊断，S1 FAIL |
| R003 | M1 | r2mu05 | 同上 | DONE | Γ=0.000, max ρ=0.000 | 5% 遗忘对照 |
| R004 | M2 | ours-inv | λ=1.0, β=0.5, 3 strategies, 2 epochs, LoRA r=8 | DONE | train loss 9.27→3.28 | `results/ours-inv/adapter` |
| R005 | M2 | ctrl-single | λ=0, β=0.5, DefaultCoT only, 2 epochs | DONE | train loss 收敛 | `results/ctrl-single/adapter` |
| R006 | M3 | ours-inv | 同 M1 + 留出策略 | DONE | Γ=0.000, retain ROUGE=0.0129 | 由执行者 B 补齐；退化为全拒答 |
| R007 | M3 | ctrl-single | 同 M1 + 留出策略 | DONE | Γ=0.000, retain ROUGE=0.0183 | 与 R006 不可区分 |
| R008 | M4 | target | budget 64/128/256/512, 20 forget | DONE | ρ(budget) 0.05→0.10 | `eval_target_budget.*` |
| R009 | M4 | r2mu01 | 同上 | DONE | ρ(budget) ≈0.10 | `eval_r2mu01_budget.*` |
| R010 | M4 | ours-inv | 同上 | DONE | ρ(budget) ≈0.00 | `eval_ours-inv_budget.*` |
| R011 | M5 | inv-λ0 / inv-λ2 | λ 消融 | SKIPPED | — | NICE-TO-HAVE；MUST 判据失败，按纪律不追加 |
| R012 | M5a | all | `recompute_leak.py` 修正实体抽取后重算 | DONE | 全部 summary `recomputed=true` | 原值存 `key_phrase_raw` / `entity_leak_raw` |
| R013 | M5b | 5 个系统 | Hy4 LLM-as-judge, 16/group, 4 策略 | RUNNING | llm_leak / 一致率 / Γ_LLM | 指标，不是独立评审 |

**判据汇总**（`analyze_results.py`）：S1 FAIL / S2 FAIL / S3 FAIL / S4 PASS（界过松，无实用价值）。

**图例**：PENDING / RUNNING / DONE / FAILED / SKIPPED。
