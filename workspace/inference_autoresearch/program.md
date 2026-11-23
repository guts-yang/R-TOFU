# Program — 推理期（Training-Free）遗忘 · 自动化研究

> 人类拥有的研究组织代码，循环期间**只读**。
> 由 `/autoresearch-loop` 结构约束驱动；方向来自 `idea-stage/inference/IDEA_REPORT.md`。

## 1. 研究对象

不改权重，只在解码时干预，使目标知识不出现在输出中。
权重哈希前后必须一致；**不宣称参数层删除**。

## 2. 单一指标（越低越好）

`val_risk = worst_leak + 0.5 * utility_drop + 0.5 * partial_leak`

- `worst_leak`：forget 集上跨策略**完整实体**命中率的最大值。
- `partial_leak`：forget 集上**部分名/长子词**命中率（例如只出现姓氏）。
  **把 C4 编进目标函数**，防止循环靠「把全名改成姓氏」作弊。
- `utility_drop = max(0, BASELINE_RETAIN_ROUGE - retain_rouge)`。
- 三者都由冻结的 `prepare.evaluate()` 计算，`train.py` 不得修改评估函数。

辅助报告量（不进目标函数）：\(\Gamma=\max\rho_d-\min\rho_d\)、各策略 \(\rho_d\)、墙钟开销。

## 3. 硬约束（不可协商）

1. **只读**：`prepare.py`、`program.md`、`calibration.json`、`pyproject.toml`、`evaluate()`。
2. **唯一可编辑代码**：`train.py`（实现推理期干预；**不做权重更新、不调用 optimizer**）。
3. **禁止新增依赖**：仅 `torch / transformers / rouge_score / numpy`。
4. **固定预算**：每轮墙钟 300 秒（`prepare.TIME_BUDGET_SEC`），超时判 crash。
5. **日志不刷屏**：`python train.py > run.log 2>&1`，只通过 grep 读指标。
6. `results.tsv` 保持 untracked；每轮只做一个单一、可解释的改动。
7. **简单性优先**：指标持平时更简单的干预胜出。
8. 不得为迎合指标改动数据、样本、阈值或评估口径。

## 4. 实现路径（对应报告 §3）

| 路径 | 干预点 | 本轮是否实现 |
|---|---|---|
| P0 安全前缀 | prompt | ✅ 基线对照 |
| P1 token/span 屏蔽 | logits | ✅ 主实验 |
| P7 跨解码一致性 | 全路径一致干预 | ✅ 由固定 3 策略评测体现 |
| P2/P3/P4 | 辅助模型 / 探针 / 隐状态 | ❌ 算力外，文献对照 |
| P5/P6 | 推测解码接受准则 / KV 回滚 | ❌ 未实现，不得宣称验证 |

## 5. 关键假设（可证伪）

- **H1** 屏蔽完整实体能降 \(\rho_d\)。
- **H2** 干预强度与保留集效用存在权衡。
- **H3** 不同解码策略对干预效果有交互（Γ 变化）。
- **H4** 完整实体被屏蔽后仍存在部分名/改写泄漏。

## 6. 停止条件（ARIS 外层预算）

`max_experiments=6`、`max_minutes=30`。到达后写 `INFERENCE_RESULTS.md` 并交接
`/research-pipeline` Stage 4。循环中不暂停询问。

## 7. 适配声明

原版 autoresearch 优化 `val_bpb` 并训练小 GPT；本仓库保留
「单文件可编辑 / 固定 300s / 单指标 / results.tsv untracked / commit-reset」全部结构约束，
指标换成本任务的 `val_risk`，运行命令由 `uv run train.py` 换为 `python train.py`
（环境已有依赖，技能禁止新增依赖）。**未运行原版 TinyStories 训练**。
