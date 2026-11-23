# 可重复执行 / 降级机制验证记录（2026-11-23）

## 1. 最优 commit 重放

`git` HEAD = `a872b16`（r09 最优状态）。重新运行 `python train.py`：

| 量 | r09 记录 | 重放 | 一致 |
|---|---|---|---|
| `val_risk` | 0.227986 | **0.227986** | ✅ |
| `worst_leak` | 0.100000 | 0.100000 | ✅ |
| `partial_leak` | 0.000000 | 0.000000 | ✅ |
| `utility_drop` | 0.255972 | 0.255972 | ✅ |
| knobs | `LR=5e-05 EPOCHS=2 W_FORGET=2.0 ... LOSS_TYPE=IDK_SFT` | 完全相同 | ✅ |

固定 seed(1001)、固定数据、固定基座、固定评测、确定性 idea 引擎 → 逐位可复现。
日志：`logs/idea_replay.out`。

## 2. LLM 思路源降级验证

`IDEA_SOURCE=llm` 单次调用（诊断标签 `HIGH_BYPASS`）：
Hy4 端点 **40.1s 超时** → `idea_engine` 自动回退确定性结果
`BYPASS_TOKENS=True`，`source=deterministic`，附 `llm_note`。

结论：降级机制按设计生效、循环不会因 LLM 不可用而中断；
但**本环境 LLM 思路源不可用**，正式循环使用确定性源，须如实标注。
日志：`logs/idea_llm_probe.out`。

## 3. 幂等性

`state.json` 在停止后为 `round=10, phase=stopped`；再次运行 driver 时
`range(11, 11)` 为空循环，不会重跑实验或破坏账本（仅重写同内容 summary）。
