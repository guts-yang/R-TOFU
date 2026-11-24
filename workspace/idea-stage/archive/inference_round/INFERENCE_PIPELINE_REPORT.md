# Research Pipeline Report — 推理期遗忘（端到端）

**Direction**: 推理阶段（training-free）遗忘机制：定义、路径、假设、实验复现与自动化研究框架
**Date**: 2026-11-23
**Pipeline**: `/research-pipeline` = idea-discovery → experiment-bridge → auto-review-loop → summary → paper-writing
**Mode**: `AUTO_PROCEED=true`, `AUTO_WRITE=false`, `assurance: draft`
**组合技能**: `/idea-discovery` + `/autoresearch-loop`（结构适配）

## Stage 状态

| Stage | 状态 | 工件 |
|---|---|---|
| 1 idea-discovery | DONE / 门控 **BLOCKED** | `idea-stage/inference/IDEA_REPORT.md`、`docs/research_contract.md` |
| 2 experiment-bridge | DONE（含 held-out 复核） | `inference_autoresearch/INFERENCE_RESULTS.md`、`redo/INFERENCE_HOLDOUT.md` |
| 3 auto-review-loop | **BLOCKED** | `review-stage/AUTO_REVIEW.md`（无跨模型评审后端） |
| 4 summary | DONE | 本报告 + `NARRATIVE_REPORT_INFERENCE.md` |
| 5 paper-writing | SKIPPED | `AUTO_WRITE=false`，venue 未指定 |

## Journey Summary

- **思路探索**：明确定义与适用/不适用边界；7 条实现路径分类（P0–P7）；
  4 个可证伪假设（H1–H4）；8 个 idea 排名；文献逐条核验并标出 3 处语境错配/未核验名。
- **实验复现**：可控基座生成式复现率 0.90；冻结评测口径；
  baseline `val_risk=0.95` → best `0.008293`（6 轮，2 keep / 4 discard / 0 crash，165.2s）。
- **自动化框架**：独立 git 仓库 + 单文件可编辑 + 300s 预算 + 单指标 +
  `results.tsv` untracked + commit/reset + 可见轮次日志 + 自动结果汇总与假设读表。
- **独立复核**：不同样本重跑，方向复现但暴露效用护栏不稳定（C2 NOT CONFIRMED）。
- **Review rounds**: 0/4（后端不可用，未伪造）。

## 关键结果（不包装成全绿）

| 判据 | 结果 |
|---|---|
| C1 有效性 | PASS（方向稳定：0.95→0.00） |
| C2 效用护栏 | **NOT CONFIRMED**（主 0.0166 通过 / held-out 0.1174 失败） |
| C3 一致性不放大 | PASS（γ ≤0.05） |
| C4 诚实报告绕过 | PASS，且发现「绕过相变」这一主结果 |

**最有价值发现**：中等强度 token 屏蔽把完整实体泄漏压到 0.15，
却让部分名绕过率升到 0.5167；只有把 bypass 写进 `val_risk`
才没有把这种「换名」误判为遗忘成功。

## Writing Handoff

- `NARRATIVE_REPORT_INFERENCE.md`: 已生成
- Venue: 未指定 → `/paper-writing` 延后
- Manual figures: ρ/partial_leak vs 干预强度曲线（数据已有，图未绘）
- 论文级宣称边界：推理期遗忘**不提供参数层保证**；token bank 为 oracle 设定；
  不含敏感内容自动发现；无跨模型评审。

## Remaining TODOs

1. 扩大 retain 样本 + 多 seed，重估 C2。
2. 实现「绕过感知」干预（把部分名/改写 token 纳入屏蔽目标）并重跑循环。
3. 需要 draft model 才能验 P5 推测解码接受准则；未实现不得写入贡献。
4. 补齐跨模型 reviewer 与 `run_state.py` / `idea_discovery_gate.py` 后重跑 Stage 1/3 门控。
