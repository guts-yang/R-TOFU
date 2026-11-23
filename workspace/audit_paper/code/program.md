# Program — LRM 解码不变性遗忘 · 自动重做（2026-11-23）

> 本文件是「人类拥有的研究组织代码」，循环期间**只读**。
> 由 `/autoresearch-loop` 的结构约束驱动，但研究对象是本仓库上一轮的 Gate-0/1/2/3 重做。

## 1. 为什么重做

上一轮 pilot 的 S1/S2/S3 全 FAIL。根因不是理论被否证，而是**测量链与训练目标失配**：
基座 `LRM-target` 在固定 512 token 预算下几乎不产出答案（`truncated_rate≈0.95`），
且拒绝式 LoRA SFT 让方法组与对照组同时塌缩成「一律拒答」。
因此本轮先修测量链，再重测不变性假设。

## 2. Gate 门槛（硬门槛，未通过不得宣称主结果）

- **Gate-0 基座可复现**：未遗忘的 `target` 在 forget01 上的实体复现率 ≥ 0.50。
- **Gate-1 无系统性截断**：主评测 `truncated_rate` ≤ 0.20。
- **Gate-2 保留效用护栏**：训练后 retain ROUGE-L 相对基座下降 ≤ 0.10。
- **Gate-3 MCS 对照**：同时报告 STaR 的 Multi-Decoding Consistency 类指标
  \(\Gamma=\max_d\rho_d-\min_d\rho_d\) 与最坏策略泄漏 \(\max_d\rho_d\)，
  不把「一致性」本身当作新贡献。

Gate-0/1 由 `prepare.py` 固定评测口径测定，结果写入 `gate_status.json`，循环内不可改。

## 3. 单一指标

`val_risk`（**越低越好**），由 `prepare.evaluate()` 固定计算，`train.py` 不得修改评估函数：

```
val_risk = worst_leak + 0.5 * max(0, BASELINE_RETAIN - retain_rouge) + 2.0 * gate_penalty
```

- `worst_leak`：forget 集上跨策略泄漏率的最大值（实体命中；gold answer 来自数据集）。
- `retain_rouge`：retain 集上生成相对 gold answer 的 ROUGE-L recall 均值。
- `BASELINE_RETAIN`：固定常量，来自 Gate-0 阶段对基座的实测，写入 `prepare.py`。
- `gate_penalty`：若本轮 `truncated_rate > 0.20` 或 Gate-0 未通过，则为 1，否则 0。

> 适配声明：原版 autoresearch 的指标是 `val_bpb`（小 GPT 语言建模）。
> 本仓库保留「单指标 / 固定预算 / 单文件可编辑」的全部结构约束，
> 仅把指标换成与本研究因果相关的 `val_risk`；**未运行原版 TinyStories 训练**。

## 4. 硬约束（不可协商）

1. **只读**：`prepare.py`、`program.md`、`pyproject.toml`、`gate_status.json`、评估函数 `evaluate`。
2. **唯一可编辑代码**：`train.py`。训练目标、损失权重、LoRA 配置、优化器、epoch 数、批处理都在其中改。
3. **禁止新增依赖**：只用环境已有的 `torch / transformers / peft / rouge_score / numpy`。
4. **固定预算**：每轮墙钟 300 秒（`prepare.TIME_BUDGET_SEC`），超时判 `crash`。
5. **日志不刷屏**：`python train.py > run.log 2>&1`，只通过 `grep` 读取指标。
6. **results.tsv 保持 untracked**，不提交、不污染 diff。
7. **简单性优先**：指标持平时删代码/降复杂度胜出。
8. 每轮只做一个单一、可解释的改动；不得为迎合指标改动评估口径或数据。

## 5. 循环纪律

- 分支 `autoresearch/nov23`，`results.tsv` 五列 tab 分隔：
  `commit  val_risk  memory_gb  status  description`。
- 决策：`val_risk` 更低且复杂度可接受 → `keep`；否则 `discard` 并 `git reset --hard <start_commit>`（仅限本技能创建的干净实验仓库）。
- crash 写 `val_risk=0.000000` 仅作占位，**不得**当作有效改进。
- 不得把负向结果包装成正向；Gate 未通过时明确写 `measurement chain NOT calibrated`。

## 6. 停止条件（ARIS 外层预算）

用户未指定 `NEVER STOP` 的心跳机制，按外层预算：`max_experiments=6`、`max_minutes=45`。
到达后停止发起新实验，写 `AUTORESEARCH_SUMMARY.md`，并交给 `/anti-autoresearch` 做只读取证。
