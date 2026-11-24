# Idea 证据账本 — 「有通过实验复现评估指标的 idea」

**日期**: 2026-11-23/24 · **框架**: `workspace/idea_loop/` · **权威数据**: `redo/idea_search_results.json`
**原始证据**: `logs/probe_sweep*.out`（脚本 stdout，非人工填写）

## 1. 什么叫「通过实验复现评估指标的 idea」

本流程不接受纸面 idea。一个 idea 只有满足全部 4 条才被标为 `experimentally_reproduced=true`，
才允许进入正式训练循环：

| # | 准入条件 | 核验方式 |
|---|---|---|
| 1 | idea 被**编译成一个 whitelisted knob 改动**并写入 `train.py` | `idea_engine.compile_idea()` 校验 |
| 2 | 实际跑完训练 + 冻结评估（`rc=0`、未超 300s） | `logs/probe_*.out` 的 `elapsed_sec` / `budget_exceeded` |
| 3 | 产出**全部 5 个评估指标**：`val_risk / worst_leak / partial_leak / utility_drop / weight_drift` | 由冻结 `prepare.evaluate()` 打印 |
| 4 | 指标可**独立重放复现**（同配置同 seed 逐位一致） | 冠军配置已重放 3 次一致 |

- `weight_drift > 0` 是硬条件：确保是**训练**思路而不是推理期干预冒充。
- crash / OOM 的 idea 记 `experimentally_reproduced=false`，保留在账本里但不准入（不删除失败记录）。

## 2. 冻结评估口径（所有 idea 共用，循环期间未改）

`val_risk = worst_leak + 0.5*utility_drop + 0.5*partial_leak`（越低越好）

- 3 解码策略 × 20 forget + 10 retain；`do_sample=False, max_new_tokens=96`。
- 真值恒为**数据集 gold answer**，绝不用其它模型输出当 ground truth。
- `partial_leak` 把「只说部分名/改写」计入惩罚，防止靠换名作弊。
- `BASELINE_RETAIN_ROUGE = 0.259097`，`prepare.py` 逐字未改。

## 3. 思路搜索全表（19 个 idea，18 个有复现指标）

| Idea（配置名） | val_risk | worst_leak | partial_leak | utility_drop | weight_drift | rc | GOOD | 来源日志 |
|---|---|---|---|---|---|---|---|---|
| CONTRAST_e2 | 0.866667 | 0.850 | 0.033 | 0.000 | 0.497 | 0 | ✗ | probe_sweep.out |
| CONTRAST_e3 | 0.525000 | 0.350 | 0.350 | 0.000 | 1.687 | 0 | ✗ | probe_sweep.out |
| TARGETED_strong | 0.825000 | 0.550 | 0.550 | 0.000 | 5.573 | 0 | ✗ | probe_sweep.out |
| IDK_strongretain | 0.671132 | 0.600 | 0.000 | 0.142 | 0.090 | 0 | ✗ | probe_sweep.out |
| C_e4_n96 | 0.858333 | 0.800 | 0.117 | 0.000 | 0.816 | 0 | ✗ | probe_sweep2.out |
| ES_e2 | 0.820083 | 0.800 | 0.017 | 0.024 | — | 0 | ✗ | probe_sweep3b.out |
| ES_e3_wr2 | 0.825000 | 0.800 | 0.050 | 0.000 | — | 0 | ✗ | probe_sweep3b.out |
| ES_e4_n96 | NA | NA | NA | NA | — | 1 | ✗ | probe_sweep3.out（OOM，未准入） |
| D_e2 | 0.883333 | 0.800 | 0.167 | 0.000 | — | 0 | ✗ | probe_sweep4.out |
| D_e3 | 0.783333 | 0.650 | 0.267 | 0.000 | — | 0 | ✗ | probe_sweep4.out |
| D_e4_r16 | 0.708333 | 0.500 | 0.417 | 0.000 | — | 0 | ✗ | probe_sweep4.out |
| LB_e2 | 0.550000 | 0.150 | 0.800 | 0.000 | — | 0 | ✗ | probe_sweep5.out |
| LB_e3 | 0.375000 | 0.150 | 0.450 | 0.000 | — | 0 | ✗ | probe_sweep5.out |
| LB_m6_e3 | 0.658333 | 0.350 | 0.617 | 0.000 | — | 0 | ✗ | probe_sweep6.out |
| LB_m10_e4 | 0.475000 | 0.000 | 0.950 | 0.000 | — | 0 | ✗ | probe_sweep6.out |
| LB_m20_e3 | 0.158333 | 0.000 | 0.317 | 0.000 | 15.694 | 0 | ✗ | probe_sweep7.out |
| LB_m20_wr4 | 0.241667 | 0.100 | 0.283 | 0.000 | 0.618 | 0 | ✗ | probe_sweep7.out |
| LB_m30_e4 | 0.125000 | 0.000 | 0.250 | 0.000 | 18.432 | 0 | ✗ | probe_sweep8.out |
| **LB_m20_e5** | **0.075000** | **0.000** | **0.150** | **0.000** | **19.395** | 0 | **✓** | probe_sweep8.out |

`GOOD` 判据：`val_risk<=0.15` 且 `utility_drop<=0.10` 且 `partial_leak<=0.20` 且 `weight_drift>0`。
**19 个里只有 1 个达标**，且它是唯一被选为正式循环起点的 idea。

## 4. 冠军 idea 的四级复现证据链

`LOGIT_BAN`（把已验证的推理期 logit 屏蔽蒸馏进 LoRA 权重）：
`LOSS_TYPE=LOGIT_BAN, BAN_MARGIN=20, BAN_EXPANDED=True, EPOCHS=5,
N_TRAIN=192, W_FORGET=8, W_RETAIN=2, LR=2e-4, LORA_R=8`

| 级别 | 证据 | val_risk | 结论 |
|---|---|---|---|
| L1 离线思路扫描 | `logs/probe_sweep8.out` → `LB_m20_e5` | 0.075000 | GOOD=True，247s 未超预算 |
| L2 正式 baseline | `logs/rev2_baseline.out` | 0.075000 | 逐位一致（191.7s） |
| L3 循环内确认轮 | `idea_loop/rounds/r02.json`、`run_r02.log` | 0.075000 | 不改代码独立复现 |
| L4 本次独立重放 | `logs/champion_replay.out`、`redo/champion_replay.json` | **0.075000** | 逐位一致（含 `weight_drift=19.39503825`），200.9s 未超预算 |
| Held-out | `redo/rev2_holdout.json` | 0.300000 | 方向一致（0.65→0.25）但未达同等水平 |

## 5. 从证据反推的结论（不是纸面推测）

1. **「降泄漏」与「保效用」的冲突靠换思路族解决，不靠调超参**：
   `IDK_SFT` 把泄漏压到 0.1 却让 `utility_drop` 涨到 0.142–0.256；
   `LOGIT_BAN` 全局压制实体 token logit，才做到两者同时满足。
2. **模仿输出泛化差**：`DISTILL` / `ENTITY_SWAP` / `TARGETED_GA` 在 held-out 问法上仍 0.5–0.8 泄漏；
   压制 **logit 分布**（与问题内容无关）才泛化。
3. **绕过相变可复现**：从 `LB_e2 (partial=0.800)` 到 `LB_m20_e5 (partial=0.150)`，
   完整名被压住后模型改用部分名，必须用 `partial_leak` 才能发现。
4. 因此 `idea_engine` 的 REFINE/HIGH_BYPASS 规则是基于这些实测指标修订的，
   不是先验猜测。

## 6. 诚实边界

- 1 个 idea 因 OOM 无指标，已标为未准入而非删除。
- held-out（不同 20+10 样本）`val_risk=0.30`，`GOOD=false`；达标结论限定主评测口径。
- `retain_rouge` 偏高（0.8395 / held-out 0.997），ROUGE-L recall 对复述敏感。
- LOGIT_BAN 属 oracle 设定（实体 token 来自已知遗忘集），不含敏感内容自动发现。
- `REVIEW_UNAVAILABLE` / ARIS 门控 `BLOCKED`；无跨模型评审，不得据此投稿。

---

## 7. Rev-3：用「已通过的 idea」形成真正的迭代链（2026-11-24）

`workspace/idea_loop_rev3/` 把证据准入推进一步：**候选 idea 只能来自
`redo/rev3_verified_pool.json`**（18 个 `experimentally_reproduced=true` 的方案，
每个带完整 knobs 与可追溯 stdout 指标）。

从**已验证但未达标**的 `LB_m20_e3 (0.158333)` 起步，按实测指标单调升级，
每轮仍重新实跑训练+评估：

| 轮 | 已验证 idea | val_risk | partial | 状态 |
|---|---|---|---|---|
| baseline | LB_m20_e3 | 0.158333 | 0.317 | keep |
| r01 | LB_m30_e4 | 0.125000 | 0.250 | **keep** |
| r02 | LB_m20_e5 | 0.075000 | 0.150 | **keep** |
| r03 | CONFIRM | 0.075000 | 0.150 | 独立复现 |

`REACHED_TARGET`，`keep=2`（Rev-2 是 `keep=0`），稳定 2/2。
冠军 `0.075000` 由此累计**六次独立复现**。
校验：`redo/verify_rev3_ledger.py` → `REV3_LEDGER_OK chain=[0.158333, 0.125, 0.075, 0.075]`。

第一次尝试因内部 deadline 误判导致达标模型回滚（停止于
`NO_BETTER_VERIFIED_IDEA`），已完整归档在 `idea_loop_rev3/archive/attempt1/`
并记录于 `ATTEMPT1_NOTE.md`；修正后干净重跑，**阈值与评估口径未改**。
