# Rev-3 第一次尝试（已作废，2026-11-24）

结果：`NO_BETTER_VERIFIED_IDEA`，3 轮 / 14.02 分钟 / keep=1。

| 轮 | idea | val_risk | good | status |
|---|---|---|---|---|
| baseline | LB_m20_e3 | 0.158333 | ✗ | keep |
| r01 | LB_m30_e4 | 0.125000 | ✗ | keep |
| r02 | LB_m20_e5 | **0.075000** | ✓ | **discard（错误）** |
| r03 | CONFIRM | 0.125000 | ✗ | discard |

**根因（实现缺陷，非阈值问题）**：`train.py` 内部保守 deadline
`T0 + 300 - 45 = 255s` 在 279.8s 的实验里提前停止训练（448/480 steps），
置 `budget_exceeded=1`；但该轮总耗时 279.8s **仍 < 300s 固定预算**、
五项指标齐全、`val_risk=0.075` 与历史逐位一致。
runner 把内部 deadline 标志当成硬失败 → `discard` 并恢复 start 快照，
导致达标模型丢失，后续确认轮只能重放 0.125，循环无更优候选而停止。

**修正**：`over` 改为按真实墙钟 `elapsed_sec > 300` 判定；
`budget_exceeded` 降级为记录字段。终止判据、`val_risk` 公式、
评估口径、idea 池、阈值**一律未改**。

第一次运行的全部账本已归档在 `archive/attempt1/`，未删除、未改写。
正式结果以修正后的第二次运行为准。
