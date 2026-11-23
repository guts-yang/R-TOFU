# EXPERIMENT PLAN — 解码不变性遗忘 Pilot

**日期**: 2026-11-23
**契约**: `idea-stage/docs/research_contract.md`
**Proposal**: `refine-logs/FINAL_PROPOSAL.md`
**算力**: 1×NVIDIA H20 96GB；预算 ≤2 GPU-hours
**代码根目录**: `/usr/local/workspace/R-TOFU/workspace/code/`
**输出根目录**: `/usr/local/workspace/R-TOFU/workspace/results/`
**Python**: `/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python`

## 固定配置（所有 run 一致）

| 项 | 值 |
|---|---|
| 目标模型 | `/jizhicfs/chenyliao/models/sangyon/LRM-target` (DeepSeek-R1-Distill-Llama-8B, bf16) |
| 遗忘集 | `/jizhicfs/chenyliao/data/rtofu/forget01.json`，`task_id=="1"` → 40 题 |
| 保留集 | `/jizhicfs/chenyliao/data/rtofu/retain90.json`，固定 seed 抽样 |
| 基线检查点 | `checkpoints/r2mu-forget01/checkpoint-last`、`checkpoints/r2mu-forget05/checkpoint-last` |
| 策略 | `DefaultCoT`, `LessThink`, `ZeroThink`, `SummaryThink`（训练/主评测用前 3 个，第 4 个作留出策略） |
| 生成 | `do_sample=False`，`DefaultCoT` max_new_tokens=512，其余 256；左 padding，batch=8 |
| 泄漏指标 | 主指标 `entity_leak`（gold answer 中目标专有实体出现在生成文本中）；副指标 ROUGE-L recall、答案命中标记 |
| 种子 | 1001 |
| 数据只读 | `/jizhicfs/chenyliao/`，不写入 |

## 运行顺序

### M0 — Sanity（MUST，先跑）
`decode_eval.py --model target --n-forget 2 --n-retain 1 --strategies DefaultCoT,ZeroThink --max-new-tokens 64`
- 判据：模型加载成功、GPU 显存 <90GB、生成非空、JSONL 与 summary JSON 落盘、无 NaN。
- 失败：按 `compute-env-contract` §5 分类（环境/路径/驱动 vs 代码），最多 2 次 patch + 2 次重写。

### M1 — 诊断基线（MUST）
对 3 个系统各跑一次 `decode_eval.py --model {target,r2mu01,r2mu05} --n-forget 40 --n-retain 20`：
- R001 `target`：遗忘前，对照 upper bound。
- R002 `r2mu01`：主诊断对象（1% 遗忘）。
- R003 `r2mu05`：5% 遗忘，检查现象是否随遗忘比例变化。
- 判据 S1：`Γ ≥ 0.15` 且 `ρ_ZeroThink − ρ_DefaultCoT ≥ 0.10`（在 R002 上）。

### M2 — 主方法训练（MUST）
- R004 `ours-inv`：`train_invariant.py --strategies DefaultCoT,LessThink,ZeroThink --lambda-cons 1.0 --beta-retain 0.5 --epochs 2 --n-forget 40`。
- R005 `ctrl-single`：`train_invariant.py --strategies DefaultCoT --lambda-cons 0.0 --beta-retain 0.5 --epochs 2 --n-forget 40`（消融对照：相同监督、无不变性）。
- 训练样本与 M1 评测样本相同集合但**评测用 gold answer 判泄漏**，监督目标为安全拒答，二者不共享标签泄漏。

### M3 — 主方法评测（MUST）
对 R004/R005 用与 M1 完全相同的 40+20 样本与 4 策略跑 `decode_eval.py`（含留出策略 `SummaryThink`）。
- 判据 S2：`Γ_ours ≤ 0.10` 且 `max_d ρ_d(ours) ≤ max_d ρ_d(r2mu01) − 0.20`；且 `Γ_ours < Γ_ctrl`。
- 判据 S3：保留集 ROUGE-L recall 相对 `target` 下降 ≤0.10。

### M4 — 预算网格与证书（NICE-TO-HAVE）
`decode_eval.py --budget-grid 64,128,256,512 --n-forget 20`，系统：`target`, `r2mu01`, `ours-inv`。
- 产出 `ρ(budget)` 曲线；用 `analyze_results.py --delta 0.1` 计算 Hoeffding 上界与覆盖率。
- 判据 S4：留出策略/预算点实测泄漏率被证书上界覆盖比例 ≥0.9（仅作可行性观察，界宽必须同时报告）。

### M5 — λ 消融（NICE-TO-HAVE，仅在 M2/M3 通过且预算有余时）
`λ_cons ∈ {0.0, 2.0}` 各一次训练+评测；对照 R004。

## 成功判据汇总

| ID | 判据 | 归属 |
|---|---|---|
| S1 | 基线存在显著"假遗忘"鸿沟 | C1 |
| S2 | 不变性模型压平鸿沟且优于单策略对照 | C2 |
| S3 | 保留集效用不明显退化 | C2 护栏 |
| S4 | 证书覆盖留出点 | C3 |

任一 MUST 判据失败 → 按「核心假设被否证 / informative negative / pilot 效能不足」分类写进结果，不得改写假设以迎合结果。

## 不在本计划内（不擅自新增实验）

- 全参训练、DPO/IRM/DRO 目标、GSM8K/MMLU 外部 benchmark、跨模型评审、真实 API 判分、多 seed 重复。
- 理由：预算与依赖受限；列为后续 `/auto-review-loop` 或人工扩展。

## 结果落盘约定

- 每次评测：`results/eval_<system>.jsonl`（逐样本）+ `results/eval_<system>.summary.json`（聚合）。
- 训练：`results/<run_id>/adapter/` + `results/<run_id>/train_args.json` + `train_log.jsonl`。
- 汇总：`refine-logs/EXPERIMENT_RESULTS.md`、`results/ANALYSIS.md`。
- 所有 JSON/JSONL 可由 `analyze_results.py` 直接读取；不得只留终端输出。


## 补充（2026-11-23 后续，执行者 B）

- **M5a `recompute`**：`code/recompute_leak.py` 修正实体抽取器后重算全部 `eval_*.jsonl` 的 `entity_leak`（原值存 `*_raw`）。原抽取器会保留 `Author ` 前缀与所有格 `'s`，系统性漏检。
- **M5b `judge`**：用户提供 `/usr/local/workspace/.env` 的 Hy4 OpenAI 兼容端点，已接入 `code/llm_judge.py` 作为**第二套泄漏指标**（见 `idea-stage/batch2/LLM_JUDGE_INTEGRATION.md`）。判分器只用于指标，**不是**跨模型独立评审。
- 生成环境已从 `bf16+KV cache` 的 `SIGFPE` 切换到可用配置；`code/decode_eval.py` 现固定 `fp32`（H20 / cu121 下 `seq_len=1` 的 bf16|fp16 linear 会触发 SIGFPE）。并行会话另装了 `torch 2.5.1+cu124` 全局环境，主结果以 `logs/full.out` 记录的实际配置为准。
- 「不在本计划内」中的「真实 API 判分」删除，现已执行。
