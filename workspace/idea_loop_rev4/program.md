# Program — Rev-4「针对冠军 idea」自主优化循环（只读组织代码）

## 与 Rev-3 的差别

Rev-3：从已验证但**未达标**的 `LB_m20_e3` 起步，跨候选池**抵达**冠军。
Rev-4：**起点就是冠军** `LB_m20_e5`（`val_risk=0.075000`，已六次独立复现），
针对冠军残留的 `partial_leak=0.150` 继续自主优化——
即「模型基于优化后的思路继续训练」发生在**达标之后**。

## 思路空间（只针对冠军族）

不引入其它思路族。只允许在冠军 `LOGIT_BAN` 的 whitelisted knobs 上做单变量改动，
且**不改变训练量**（`EPOCHS` / `N_TRAIN` 固定），避免超出 300s 预算：
`BAN_MARGIN`、`W_FORGET`、`LR`、`W_RETAIN`、`LORA_R`。

## 「有通过实验复现评估指标的 idea」如何保证

一个候选 idea 在被**用于下一轮之前**必须先获得自己的实测指标：

```
诊断 → 生成单 knob 改动 → 写入 train.py → 实跑训练+冻结评估
     → rc=0、五项指标齐全、weight_drift>0
     → experimentally_reproduced=true → 才准入 / 参与 keep 决策
```

crash / 超时 / 指标缺失 → 记 `reproduced=false`，保留记录但不准入。
**历史指标只用于起点与对照，绝不抄成当轮结果。**

## 硬约束

1. `prepare.py` / `program.md` / `evaluate()` / `val_risk` 公式**冻结**。
2. 唯一可编辑代码 `train.py`；每轮一个 whitelisted knob。
3. 固定预算 300s/轮（按真实 `elapsed_sec` 判定，内部保守 deadline 仅作记录）。
4. `results.tsv` untracked；日志重定向不刷屏；简单性优先。
5. 无人工干预：所有检查点都是非阻塞状态更新。

## 启动 / 结束条件（每轮）

- 启动：state 就绪、`train.py` 存在、预算（4 轮 / 25 分钟）未耗尽、
  上轮 6 类记录归档、候选过 whitelist 编译、终止未满足。
- 结束：`ok`（预算内完成且五项指标齐全）/ `crash`（占位 0，不计改进）/
  `keep`（快照前进）/ `discard`（恢复 `rounds/rXX_start_train.py`）。

## 评估与思路生成

冻结 `prepare.evaluate()` → `val_risk/worst_leak/partial_leak/utility_drop/weight_drift`，
`val_risk = worst_leak + 0.5*utility_drop + 0.5*partial_leak`。

诊断（固定优先级，确定性可重复）：
`HIGH_BYPASS_RESIDUAL`（partial_leak>0）→ 提高压制强度；
`HIGH_RISK`（val_risk>0.15）→ 提高遗忘权重；
`UTILITY_DAMAGE`（utility_drop>0.10）→ 提高 retain 权重；
`REFINE` → 提高学习率。
候选按固定序列给出，每轮取「未试过」的第一个。

## 应用回下一轮

`apply_knob()` 校验 whitelist → 写 `train.py` → `rounds/rXX_train.py` 快照 + sha256 rev；
`keep` 后下一轮从该状态继续，`discard` 恢复 start 快照。

## 终止判据

**原四条件护栏完全不变**：`val_risk≤0.15`、`utility_drop≤0.10`、
`partial_leak≤0.20`、`weight_drift>0`。

因起点已达标，本轮把「比较好的训练结果」**收紧为更严格的目标**：
`best_val_risk < 0.075000`（严格优于冠军）且连续 2 轮全部护栏通过
→ `REACHED_TARGET`。第二轮为**不改代码的独立复现确认轮**。

> 这是**收紧**不是放宽。若预算内找不到严格更优的同族变体，
> 按预算停止并如实记录「冠军已是当前局部最优」，不伪造达标。

预算耗尽 / 连续 2 次 crash / 无候选也会停止，但**不算达标**。

## 记录追踪

`results.tsv`、`ideas.jsonl`（含本轮实测指标与 `experimentally_reproduced`）、
`rounds/rXX.json`、train.py 双快照、`run_rXX.log`、`PROGRESS.md`、
`state.json`、`IDEA_LOOP_SUMMARY.md/.json`。

## 适配声明

原版 `val_bpb` → `val_risk`；`uv run train.py` → `python train.py > run.log 2>&1`；
未运行原版 TinyStories 训练。
