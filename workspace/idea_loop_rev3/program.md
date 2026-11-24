# Program — Rev-3「针对已通过的 idea」自动训练循环（只读组织代码）

## 与 Rev-2 的唯一差别

Rev-2 达标但 `keep=0`：起点已是冠军，生成的 idea 未改进即回退，
没有形成「基于优化后的思路继续训练」的迭代链。

Rev-3 的 idea **只能来自 `redo/rev3_verified_pool.json`**——
18 个已通过实验复现评估指标（`experimentally_reproduced=true`）的方案，
每个都带完整 whitelisted knobs 与实测指标。
流程从其中**已验证但未达标**的一个起步，按实测指标单调升级，
每轮实跑验证后 `keep`，形成真正的迭代链。

## 硬约束（不可协商）

1. `prepare.py` / `program.md` / 评估函数 `evaluate()` **冻结**；`val_risk` 公式与阈值未改。
2. 唯一可编辑代码 `train.py`；每轮应用一个已验证 idea 的**整组 knobs**（仍只改这一个文件）。
3. 每轮必须**重新实跑训练+评估**，禁止直接抄用池里的历史指标作为本轮结果。
4. 固定预算 300s/轮；`results.tsv` untracked；日志重定向，不用 tee。
5. 简单性优先：候选按实测 `val_risk` 选「比当前更优的最小改进」。
6. 无人工干预：所有检查点都是非阻塞状态更新。

## 启动 / 结束条件（每轮）

- 启动：state 就绪、`train.py` 存在、预算未耗尽、上轮 6 类记录归档、
  候选 idea 已通过 whitelist 编译、终止条件未满足。
- 结束：`ok`（训练+评估在预算内完成且五项指标齐全）/ `crash`（占位 0，不计改进）/
  `keep`（快照前进）/ `discard`（恢复 start 快照）。

## 评估与思路生成

冻结 `prepare.evaluate()` → `val_risk/worst_leak/partial_leak/utility_drop/weight_drift`。
诊断标签：`HIGH_BYPASS` (partial>0.20) / `HIGH_RISK` (val_risk>0.15) /
`UTILITY_DAMAGE` (utility_drop>0.10) / `REFINE`。
从池中筛选 `val_risk < 当前实测值`、`utility_drop<=0.10`、未试过者，
取实测值最接近当前的一个（最小有效改进）作为「优化思路」。
**优化思路因此是被实验复现指标验证过的，不是语言推测。**

## 应用回下一轮

`apply_config()` 校验每个 knob 在 `idea_engine.WHITELIST` 内 → 写入 `train.py`
→ 保存 `rounds/rXX_train.py` 快照 + sha256 rev → 下一轮从该状态启动；
discard 恢复 `rounds/rXX_start_train.py`。

## 终止判据（未放宽）

连续 2 轮同时满足 `val_risk<=0.15`、`utility_drop<=0.10`、
`partial_leak<=0.20`、`weight_drift>0` → `REACHED_TARGET`。
确认轮为**不改代码的独立复现**；预算(6 轮/25 分钟)、连续 2 次 crash、
无可用候选也会停止，但**不算达标**。

## 记录追踪

`results.tsv`、`ideas.jsonl`、`rounds/rXX.json`、train.py 双快照、
`run_rXX.log`、`PROGRESS.md`、`state.json`、`IDEA_LOOP_SUMMARY.md/.json`。

## 适配声明

原版 autoresearch 的 `val_bpb` 换为本任务 `val_risk`，
`uv run train.py` 换为 `python train.py > run.log 2>&1`；未运行原版 TinyStories 训练。
