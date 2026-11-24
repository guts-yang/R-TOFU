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


## 追加工件（推理期遗忘轮）

| 路径 | 说明 |
|---|---|
| `idea-stage/inference/IDEA_REPORT.md` | 定义/边界/路径分类/假设/排名 + 实测回填 |
| `idea-stage/inference/docs/research_contract.md` | C1–C4 契约 |
| `inference_autoresearch/` | 独立 git 仓库：`program.md`/`prepare.py`(冻结)、`train.py`(唯一可编辑、不更新权重)、`calibration.json`、`results.tsv`、`INFERENCE_RESULTS.md`、`PREFLIGHT_NOTE.md` |
| `redo/infer_base_probe.py` | 基座生成式复现率探针（0.90） |
| `redo/infer_holdout_check.py` / `.json` | 独立样本复核 |
| `redo/INFERENCE_HOLDOUT.md` | 复核结论与 C2 未确证 |
| `redo/inference_runner.py` | 6 轮循环驱动器（实验仓库之外） |
| `INFERENCE_PIPELINE_REPORT.md` | research-pipeline Stage 状态 |
| `NARRATIVE_REPORT_INFERENCE.md` | W4 交接稿 |

本轮判定：C1 PASS / **C2 NOT CONFIRMED** / C3 PASS / C4 PASS（绕过相变为主发现）。
Stage 3 仍 `BLOCKED`，门控 `BLOCKED`。


## 追加工件（Idea-in-the-Loop 轮）

| 路径 | 说明 |
|---|---|
| `idea_loop/DESIGN.md` | 用户 5 点要求的流程设计 + 实测补充 |
| `idea_loop/program.md` / `prepare.py` / `calibration.json` / `idea_engine.py` | 只读组织代码、冻结评测、思路引擎 |
| `idea_loop/train.py` | 唯一可编辑、真实更新权重（`weight_drift>0`） |
| `idea_loop/results.tsv` / `ideas.jsonl` / `rounds/` / `run_rXX.log` / `PROGRESS.md` / `state.json` | 全链路追踪，支持 `--resume` |
| `idea_loop/IDEA_LOOP_SUMMARY.md` / `REPLAY_NOTE.md` / `PREFLIGHT_NOTE.md` | 汇总、可重复性验证、诚信记录 |
| `redo/idea_loop_runner.py` / `redo/IDEA_LOOP_REPORT.md` | 驱动器与五点逐项对照报告 |
| `idea-stage/idea_loop/IDEA_REPORT.md` | 思路池的实证排名与修订 |

本轮终止：`BUDGET_EXHAUSTED_ROUNDS`，best 0.227986 > 目标 0.15，**未达标**；
门控 `BLOCKED` / `REVIEW_UNAVAILABLE` 不变。


## 追加工件（Rev-2 达标轮）

| 路径 | 说明 |
|---|---|
| `redo/IDEA_LOOP_REV2_REPORT.md` | 五点对照 + 达标结果 + 诚实边界 |
| `redo/probe_sweep*.py` / `redo/idea_search_results.json` | 自动思路搜索（16+ 训练思路） |
| `redo/rev2_final_runner.py` | 内容哈希 + 文件快照的循环驱动器 |
| `redo/rev2_holdout_check.py` / `rev2_holdout.json` | 达标模型 held-out 复核 |
| `idea_loop/REVISION_NOTE.md` | 阈值未放宽的修订边界 |
| `idea_loop/archive/rev1/` | Rev-1 完整账本归档（未删改） |
| `idea_loop/IDEA_LOOP_SUMMARY.md` | **`REACHED_TARGET`**、`val_risk=0.075000` |
| `idea_loop/distill_targets.json` / `build_distill_targets.py` | 自蒸馏教师缓存（循环前一次性） |

**本轮终止 `REACHED_TARGET`（未放宽阈值）**；held-out `val_risk=0.30` 为已知边界。
门控 `BLOCKED` / `REVIEW_UNAVAILABLE` 不变。


## 追加：Idea 证据准入轮

| 路径 | 说明 |
|---|---|
| `idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md` | idea → 实验 → 五项指标 → 复现状态逐条绑定 |
| `redo/idea_search_results.json` | 权威账本：19 idea / 18 有复现指标 / 1 GOOD |
| `redo/verify_idea_evidence.py` | 确定性校验：每条指标可追溯到原始 stdout |
| `logs/probe_sweep*.out` | 原始实验输出（非人工填写） |
| `logs/champion_replay.out` / `redo/champion_replay.json` | 冠军 idea 第四次独立重放 |
| `idea_loop/DESIGN.md §9`、`program.md` | 只读的 Idea Evidence Gate |

校验结果：`EVIDENCE_OK ideas=19 reproduced=18 GOOD=1 champion_vals=[0.075, 0.075]`。
门控 `BLOCKED` / `REVIEW_UNAVAILABLE` 不变。


## 追加：Rev-3 已验证 idea 迭代链（最终交付）

| 路径 | 说明 |
|---|---|
| `idea_loop_rev3/program.md` | 只读组织代码：idea 只能来自已实验复现的池 |
| `idea_loop_rev3/rev3_runner.py` | 单调改进链驱动器（内容哈希 + 双快照） |
| `idea_loop_rev3/IDEA_LOOP_SUMMARY.md` / `results.tsv` | **`REACHED_TARGET`、keep=2、稳定 2/2** |
| `idea_loop_rev3/ATTEMPT1_NOTE.md` / `archive/attempt1/` | 第一次尝试失败原因与完整归档 |
| `redo/rev3_verified_pool.json` | 18 个已复现 idea 的完整配置 + 实测指标 |
| `redo/verify_rev3_ledger.py` | 确定性校验 `chain=[0.158333, 0.125, 0.075, 0.075]` |
| `redo/IDEA_LOOP_REV3_REPORT.md` | 五点对照 + 结果 + 诚信记录 + 边界 |

链路：`0.158333 → 0.125000 → 0.075000 → 确认 0.075000`。
门控 `BLOCKED` / `REVIEW_UNAVAILABLE` 不变。


## 追加：idea 文档归档（2026-11-24）

按用户要求保留**冠军 idea `LOGIT_BAN`** 相关文档，其余失败/被淘汰轮次的
idea 报告迁移到 `idea-stage/archive/`（**只移动、未删除**）。

- 主入口：`idea-stage/CHAMPION_IDEA.md`（冠军指标、配置、六次复现、故事、边界）
- 归档清单与恢复命令：`idea-stage/ARCHIVE_MANIFEST.md`
- 保留：`idea-stage/idea_loop/{IDEA_REPORT,IDEA_EVIDENCE_LEDGER}.md`、
  `idea-stage/inference/IDEA_REPORT.md`、`inference/docs/research_contract.md`；
  用户原始输入 `idea-1.md`/`idea-2.md` 原位不动。
- 归档：第一批 `IDEA_REPORT.md` + 契约、第二批 `batch2/` 四个文件、`redo/IDEA_LOOP_REPORT.md`。
- 实验证据（probe 日志、证据账本、校验脚本、实验仓库）**不归档**，以维持冠军可复现性。
- 归档后三项确定性校验结果不变。


## 追加：冠军机制讲解 HTML（2026-11-24）

- Markdown 源（唯一真实来源）：`idea-stage/CHAMPION_LOGIC.md`
- 渲染产物：`idea-stage/CHAMPION_LOGIC.html`（`/render-html`，academic 模板，单文件）
- 附带证据：`--json redo/champion_replay.json`；漂移 meta 含源路径 + SHA256 + 生成时间
- 评审 sidecar：`CHAMPION_LOGIC.html.review.json` → **`REVIEW_UNAVAILABLE`**（无跨模型 reviewer 后端，未伪造 PASS）
- 内容：可控基座 → 冻结评测指标 → `LOGIT_BAN` 四步机制 → 排除法证据 →
  绕过相变 → 自动化迭代链 → 结果与边界 → 代码索引


## 追加：第二次 idea 归档（2026-11-24）

按「主线保留、其它 ideas 相关文件归档」扩展到全工作区，新增归档 15 个文件
（顶层 2 个推理期报告、`redo/INFERENCE_HOLDOUT.md`、`REDO_REPORT.md`、
5 个旧 runner、6 个 sweep 中间 json），`idea-stage/archive/` 累计 22 个文件。
清单、判据与恢复命令见 `idea-stage/ARCHIVE_MANIFEST.md §7`。

**保留的主线**：`CHAMPION_IDEA.md`、`CHAMPION_LOGIC.md/.html`、
`idea_loop/{IDEA_REPORT,IDEA_EVIDENCE_LEDGER}.md`、`inference/IDEA_REPORT.md` 与契约、
用户原始输入；以及冠军证据链（权威账本、probe 脚本与日志、校验脚本、
达标报告、诊断证据、四个实验仓库）。
归档后三项确定性校验与 HTML 源 SHA256 均不变。

> 注意：此前索引中提到的 `INFERENCE_PIPELINE_REPORT.md`、
> `NARRATIVE_REPORT_INFERENCE.md`、`REDO_REPORT.md` 等路径现已移到
> `idea-stage/archive/` 下，按 §7 清单查找。
