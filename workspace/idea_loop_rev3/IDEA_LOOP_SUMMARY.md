# Rev-3 — 针对「已通过的 idea」的自动训练迭代链

- 终止原因: **REACHED_TARGET**
- 起点 idea: `LB_m20_e3`（已实验复现，val_risk=0.158333，未达标）
- 最佳 `val_risk`: **0.075000**（目标 ≤ 0.15）
- 轮数 3/6，耗时 12.71 分钟，稳定 2/2
- keep/discard/crash/confirm = 2/1/0/1

## 单调改进链（每轮 idea 均来自已实验复现的池）

| r | idea | 来源 | val_risk | worst | partial | utility_drop | 状态 |
|---|---|---|---|---|---|---|---|
| baseline | LB_m20_e3 | verified_pool | 0.158333 | 0.000000 | 0.316667 | 0.000000 | keep |
| 01 | LB_m30_e4 | verified_pool | 0.125000 | 0.000000 | 0.250000 | 0.000000 | keep |
| 02 | LB_m20_e5 | verified_pool | 0.075000 | 0.000000 | 0.150000 | 0.000000 | keep |
| 03 | CONFIRM | confirmation | 0.075000 | 0.000000 | 0.150000 | 0.000000 | discard |

## 五点要求

1. **启动/结束**：state 就绪、预算、上轮归档、idea 过 whitelist 编译；`ok/crash/keep/discard`。
2. **评估并生成思路**：冻结 `prepare.evaluate()` 五项指标 → 诊断标签 → 从 18 个已复现 idea 中挑严格更优、护栏通过、未试过的最小改进。
3. **应用回下一轮**：整组 whitelisted knobs 写入 `train.py` → 快照 + sha256 rev；keep 后下一轮从该状态继续；discard 恢复 start 快照。
4. **终止判据（未放宽）**：连续 2 轮 `val_risk<=0.15` 且 `utility_drop<=0.1` 且 `partial_leak<=0.2` 且 `weight_drift>0`；确认轮为不改代码的独立复现。
5. **记录追踪**：`results.tsv`、`ideas.jsonl`、`rounds/rXX.json`、train.py 双快照、`run_rXX.log`、`PROGRESS.md`、`state.json`、本文件。

## 与 Rev-2 的差别

Rev-2 达标但 `keep=0`（起点已是冠军，无迭代链）。Rev-3 从未达标的已验证 idea 起步，每个优化思路都来自**有实验复现评估指标**的池，且每轮**重新实跑训练+评估**，形成真实的单调改进链。阈值、评估口径、`val_risk` 公式一律未改。
