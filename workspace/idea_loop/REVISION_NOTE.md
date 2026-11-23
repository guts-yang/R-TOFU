# Rev-2 修订说明（2026-11-23 → 11-24）

Rev-1 循环终止于 `BUDGET_EXHAUSTED_ROUNDS`（best 0.227986 > 0.15，utility_drop 0.256）。
诊断为两个真实缺陷，本轮在**循环开始前**一次性修订：

1. **目标函数与终止条件不一致**：Rev-1 的 `val_risk` 中 utility_drop 权重仅 0.5，
   使「一律拒答」的 IDK_SFT 被判为最优。Rev-2 在 keep 决策加**硬护栏**：
   `utility_drop > 0.10` 的轮次即使 val_risk 更低也 discard。
2. **可用思路里缺「既降泄漏又保效用」的方法**：Rev-1 只有 GA_GD / IDK_SFT。
   Rev-2 新增 TARGETED_GA / CONTRAST / ENTITY_SWAP / DISTILL / **LOGIT_BAN**
   （把已验证的推理期 logit 屏蔽蒸馏进权重），并新增 BAN_MARGIN / BAN_EXPANDED / N_TRAIN。
3. **稳定计数改为基于 `good(m)`**，并新增**不改代码的独立复现确认轮**：
   「连续 2 轮达标」现在是一次真实的重现验证，而不是靠两次偶然改进。

**没有改变的东西（关键）**：
- `prepare.py` 冻结评测**逐字未改**（同一批 20+10 样本、同一阈值、同一 baseline 0.259097）；
- 终止判据数值**未放宽**：仍为 `val_risk<=0.15`、`utility_drop<=0.10`、
  `partial_leak<=0.20`、`weight_drift>0`，连续 2 轮；
- 单指标 `val_risk` 公式未改；固定 300s 预算未改。

**思路搜索阶段（自动化、无人干预）**：`redo/probe_sweep*.py` 共扫描 16+ 个训练思路，
结果在 `redo/idea_search_results.json`；冠军 `LOSS_TYPE=LOGIT_BAN, BAN_MARGIN=20,
EPOCHS=5, N_TRAIN=192, W_FORGET=8, W_RETAIN=2, LR=2e-4, BAN_EXPANDED=True`
在离线扫描中达到 `val_risk=0.075, worst_leak=0, partial_leak=0.15, utility_drop=0`
（247s，未超预算）。该配置作为 Rev-2 正式循环的起点（「优化后的思路」）。

Rev-1 全部账本已归档在 `archive/rev1/`，未被删除或改写。
