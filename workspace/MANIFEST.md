# Artifact Manifest

> 工件数 > 15，按 Output Manifest Protocol 维护。MD/JSON 为唯一真实来源；
> 本文件只做索引，不复制结论。所有路径相对 `/usr/local/workspace/R-TOFU/workspace/`。

## 研究契约与报告

| 文件 | 状态 | 说明 |
|---|---|---|
| `idea-stage/idea-1.md` | 用户提供 | 第一批 Idea 1 设计草案（只读） |
| `idea-stage/idea-2.md` | 用户提供 | 第二批 10 个 idea 报告（只读，未改写） |
| `idea-stage/IDEA_REPORT.md` | 生成 | 第一批 W1 报告；门控 BLOCKED |
| `idea-stage/docs/research_contract.md` | 生成 | W1→W1.5 聚焦契约 |
| `idea-stage/batch2/REPRO_AUDIT.md` | 生成 | 第二批环境/引用复现审计 |
| `idea-stage/batch2/IDEA_REPORT.md` | 生成 | 第二批 Round 1（全量复现） |
| `idea-stage/batch2/IDEA_REPORT_round2.md` | 生成 | 第二批 Round 2（再次 idea-discovery） |
| `idea-stage/batch2/LLM_JUDGE_INTEGRATION.md` | 生成 | Hy4 判分接入与限制 |
| `refine-logs/FINAL_PROPOSAL.md` | 生成 | 方法提案 |
| `refine-logs/EXPERIMENT_PLAN.md` | 生成 | M0–M5 计划 |
| `refine-logs/EXPERIMENT_TRACKER.md` | 生成 | 真实执行状态 |
| `refine-logs/EXPERIMENT_RESULTS.md` | 自动生成 | `analyze_results.py` 输出 |
| `results/ANALYSIS.md` | 自动生成 | 同上（副本） |
| `NARRATIVE_REPORT.md` | 生成 | W4 交接稿 |
| `RESEARCH_PIPELINE_REPORT.md` | 生成 | 流水线阶段状态 |
| `review-stage/AUTO_REVIEW.md` | 生成 | Stage 3 BLOCKED 说明 |

## 代码（`code/`）

| 文件 | 作用 |
|---|---|
| `paths.py` | 路径注册表；数据/模型只读自 `/jizhicfs/chenyliao/` |
| `data_utils.py` | 数据加载 + 敏感实体抽取（已修正 `Author `/`'s`） |
| `strategies.py` | 4 种解码策略 prompt |
| `leak_metrics.py` | 实体泄漏 / ROUGE-L 指标 |
| `decode_eval.py` | 跨策略生成与评测（fp32 + KV cache） |
| `train_invariant.py` | LoRA 不变性训练与单策略对照 |
| `recompute_leak.py` | 修正抽取器后重算 `entity_leak`，保留 `*_raw` |
| `llm_judge.py` | Hy4 LLM-as-judge（指标，非评审） |
| `analyze_results.py` | 聚合、S1–S4 判据、证书、判分对照 |
| `run_all.sh` | 编排脚本 |
| `diag*.py` / `logs/diag*.log` | SIGFPE 定位证据（诊断脚本可删，日志保留） |

## 结果（`results/`）

- `eval_<tag>.jsonl` / `.summary.json`：逐样本与聚合；`recomputed=true`。
- `eval_<tag>_budget.*`：推理预算网格 64/128/256/512。
- `judge_<tag>.jsonl` / `.summary.json`：Hy4 判分；失败样本 `judge_ok=0`。
- `ours-inv/` / `ctrl-single/`：LoRA adapter、`train_args.json`、`train_log.jsonl`。

## 日志（`logs/`）

`full.out`（并行会话全量实验）、`sanity*.out`、`diag*.log`（SIGFPE 矩阵定位）、
`recompute.out`、`judge*.out`、`eval_ours-inv.out`、`run_all.log`。

## 证据等级

- 所有实验数字可追溯到 `results/*.jsonl`；未通过跨模型评审（`REVIEW_UNAVAILABLE`）。
- 证据门控 `BLOCKED`（缺 ARIS helper）；不得当作 submission-ready 交付。


## 追加工件（自动重做轮）

| 路径 | 说明 |
|---|---|
| `redo/REDO_REPORT.md` | Gate-0/1/2/3 + autoresearch + 取证综合报告 |
| `redo/gate0_probe.py` / `gate0_probe.json` | 基座复现率诊断 |
| `redo/teacher_force_check.py` | gold-answer NLL 诊断 |
| `redo/autoresearch_runner.py` | 6 轮循环驱动器（位于实验仓库之外） |
| `autoresearch/` | 独立 git 仓库：`program.md`/`prepare.py`(冻结)、`train.py`(唯一可编辑)、`results.tsv`、`AUTORESEARCH_SUMMARY.md`、`AUDIT_FEEDBACK.md`、`gate_status.json`、`PREFLIGHT_NOTE.md` |
| `audit_paper/` | Anti 取证 PAPER_DIR：`submission.tex`、`claims.json`、`report.json`、`REPORT.md`、4 个 `*.findings.json`、`coverage.json` |

证据等级补充：Anti 审计为**确定性-only**，verdict `REVIEW_UNAVAILABLE`（L2），
不是 `CLEAN_GIVEN_EVIDENCE`，不得当作放行。
