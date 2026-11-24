# NARRATIVE REPORT — 推理期遗忘（W4 交接稿）

**日期**: 2026-11-23 · **状态**: `assurance: draft`；Stage 3 `REVIEW_UNAVAILABLE`；门控 `BLOCKED`

## 1. Problem & Definition

不改权重，只在解码时干预使目标知识不出现在输出中；按请求启用、可撤销。
适用：闭源/服务化、多租户、即时删除、运行时审计。
不适用：参数层保证、黑盒无 logit、超大规模长期删除、对抗改写。
**明确不宣称「模型里已删除」。**

## 2. Method

- 可控基座 `autoresearch/base_merged`（生成式实体复现率 0.90）。
- 干预：P0 安全前缀、P1 token logit 屏蔽（α=5 / α=20 / -inf）、组合、扩大 bank。
- 冻结评测：3 解码策略 × 20 forget + 10 retain，`do_sample=False, max_new_tokens=96`。
- 单指标 `val_risk = worst_leak + 0.5*utility_drop + 0.5*partial_leak`。
- 自动化：独立 git 仓库、单文件可编辑、300s 预算、6 轮 commit/reset 循环。

## 3. Key Results（可追溯到 `inference_autoresearch/results.tsv`）

| 系统 | val_risk | worst_leak | partial_leak | γ | retain_rouge |
|---|---|---|---|---|---|
| 无干预 baseline | 0.950000 | 0.950000 | 0.000000 | 0.0 | 0.259097 |
| 安全前缀 | 0.986994 | 0.950000 | 0.000000 | 0.0 | 0.185108 |
| 屏蔽 α=5 | 0.408333 | 0.150000 | **0.516667** | 0.1 | 0.268141 |
| 屏蔽 α=20（best） | **0.008293** | 0.000000 | 0.000000 | 0.0 | 0.242511 |
| 硬屏蔽 -inf | 0.008293 | 0.000000 | 0.000000 | 0.0 | 0.242511 |

Held-out（不同 20+10 样本）：none 0.65/0.05、α=5 0.25/**0.3333**、α=20 0.00/0.0833；
retain_rouge 0.5666→0.4492（下降 **0.1174**）。见 `redo/INFERENCE_HOLDOUT.md`。

## 4. Claims & Evidence

| Claim | 判定 | 证据 |
|---|---|---|
| C1 屏蔽降低泄漏 | PASS（方向稳定） | 主循环 + held-out |
| C2 效用护栏 | **NOT CONFIRMED** | 主 0.0166 通过 / held-out 0.1174 失败 |
| C3 不放大跨策略不一致 | PASS | γ ≤0.05 全程 |
| C4 绕过必须报告 | PASS（主发现） | α=5 的 partial_leak 跃升 |

**核心叙事**：推理期遗忘存在「绕过相变」——中等强度干预只是把完整名换成部分名；
只有把 bypass 惩罚写入优化目标，自动研究才不会把这种换名误判为成功。

## 5. Limitations

- oracle token bank（473 ids 来自 forget01 全部实体名），不含敏感内容自动发现。
- 20+10 样本、单基座、单 split、无 seed 重复；绝对值对样本敏感。
- `weight_drift=0` 只在本实现内验证；不验证第三方部署。
- 推理期遗忘不提供参数层保证；成员推断/白盒探针仍可能恢复知识。
- 无跨模型评审、无 ARIS 门控 helper；`BLOCKED` / `REVIEW_UNAVAILABLE` 不变。
- P2/P3/P4 为文献对照，P5/P6 未实现，不得写入贡献。

## 6. Figure / Table Inventory

- 主结果表：已生成（MD 表，见 §3）
- ρ / partial_leak vs α 曲线：数据已有（`results.tsv`），**论文级图未绘**
- 训练/生成日志：`inference_autoresearch/run.log`、`logs/inference_loop2.out`

## 7. Handoff

Venue 未指定、`AUTO_WRITE=false` → `/paper-writing` 未执行。
补齐 reviewer 与门控 helper 后重跑 Stage 3，再考虑投稿。
