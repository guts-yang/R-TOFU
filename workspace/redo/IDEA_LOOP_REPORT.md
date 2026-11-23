# Idea-in-the-Loop 自动训练流程 — 设计与实测报告

**日期**: 2026-11-23 · **技能**: `/idea-discovery` + `/autoresearch-loop`
**框架**: `workspace/idea_loop/`（独立 git 仓库，分支 `autoresearch/idealoop23`）
**驱动器**: `redo/idea_loop_runner.py` · **详细设计**: `idea_loop/DESIGN.md`

## 用户要求逐项对照

### ① 每轮训练的启动与结束条件 → `DESIGN.md §1`

**启动**（6 条全部满足）：`state.json` 就绪 / git 工作区干净 /
基座校验通过（生成式复现率 0.90）/ 预算未耗尽（`round<10`、`elapsed<35min`）/
上一轮 6 类记录已归档 / 本轮 idea 已通过 whitelist 编译。

**结束**：300s 内完成训练+评估并产出全部指标 → `ok`；
超时或指标缺失 → `crash`（`val_risk=0` 占位，**不计为改进**）；
结果落盘后按严格下降判定 `keep`（commit 前进）或 `discard`（`reset --hard`）。

实测：10 轮全部正常结束，0 crash、0 超时，最长单轮 < 60s。

### ② 评估当前结果并生成优化思路 → `idea_loop/idea_engine.py`

冻结评估 `prepare.evaluate()`：3 解码策略 × 20 forget + 10 retain，
输出 `worst_leak / partial_leak / gamma / retain_rouge / utility_drop`，
单指标 `val_risk = worst_leak + 0.5*utility_drop + 0.5*partial_leak`。

**确定性诊断→idea 规则表**（固定优先级，同输入同输出）：
`HIGH_BYPASS → BYPASS_TOKENS`、`UTILITY_DAMAGE → W_RETAIN/LR`、
`HIGH_LEAK → W_FORGET/EPOCHS`、`CROSS_STRATEGY_GAP → INV_LAMBDA`、
`STAGNATION → 结构性 pivot (LOSS_TYPE)`。

**诚实说明**：默认 `IDEA_SOURCE=deterministic`，即由**规则引擎**生成思路，
不是 LLM 自主创造；这换来完全可重复。可选 `IDEA_SOURCE=llm` 调用 Hy4
（`/usr/local/workspace/.env`）返回严格 JSON，经 whitelist 校验后采用，
失败自动回退确定性。hy4 与执行者同家族，**只是 idea 生成器，不是独立评审**。

实测 idea 演化（自动切换 family，无需人工）：
`HIGH_LEAK(×3) → HIGH_BYPASS(×2) → HIGH_LEAK → STAGNATION → UTILITY_DAMAGE(×3)`。

### ③ 优化思路应用回下一轮 → `apply/compile_idea`

`compile_idea()` 只接受 whitelist 内 `knob/value`，正则替换 `train.py` **一个**常量，
`git commit -m "rXX: <idea>"` 形成不可变快照；下一轮从该 commit 启动（思路继承）。
若上一轮 discard 则先 reset 回起点。除 `train.py` 外所有文件冻结。

### ④ 终止判断标准（何为「比较好的训练结果」）→ `DESIGN.md §4`

连续 **2 轮**同时满足：
`val_risk<=0.15` 且 `utility_drop<=0.10` 且 `partial_leak<=0.20` 且 `weight_drift>0`。
另设预算停止（10 轮 / 35 分钟）、连续 2 次 crash、无可用 idea；
**这些都不算达标**。停滞 3 轮不停止，而是强制结构性 pivot。

**实测终止**：`BUDGET_EXHAUSTED_ROUNDS`，10 轮 / 7.97 分钟，
best `0.227986 > 0.15`，`stable_count=0/2` → **未达标，如实记录**。
最优轮 `utility_drop=0.255972 > 0.10`，护栏确实拦住了「只看泄漏不看效用」的假成功。

### ⑤ 记录与追踪 → `DESIGN.md §5`

| 文件 | 实测状态 |
|---|---|
| `results.tsv` | 11 行（表头+1 baseline+10 轮），untracked |
| `ideas.jsonl` | 10 条（诊断/idea/knob/value/family/source/是否接受） |
| `rounds/r01..r10.json` | 完整指标+commit+状态快照，10 个 |
| `run_r01..r10.log` | 每轮日志归档，10 个 |
| `PROGRESS.md` | 每轮追加可读进度 |
| `state.json` | round/best/stable/no_improve/crashes/tried/phase，支持 `--resume` |
| git 分支 | 10 个 idea commit，discard 已 reset |

## 实测结果

| r | 诊断 | idea (knob=value) | val_risk | 状态 |
|---|---|---|---|---|
| baseline | — | GA_GD 24 steps | 0.950948 | keep |
| 01 | HIGH_LEAK | `W_FORGET=2.0` | 0.950000 | keep |
| 02 | HIGH_LEAK | `W_FORGET=4.0` | 1.008333 | discard |
| 03 | HIGH_LEAK | `EPOCHS=2` | 0.633786 | keep |
| 04 | HIGH_BYPASS | `BYPASS_TOKENS=True` | 0.683333 | discard |
| 05 | HIGH_BYPASS | `W_FORGET=0.5` | 0.916667 | discard |
| 06 | HIGH_LEAK | `GA_CLIP=12.0` | 0.633786 | discard |
| 07 | **STAGNATION** | `LOSS_TYPE="IDK_SFT"` | 0.232897 | keep |
| 08 | UTILITY_DAMAGE | `W_RETAIN=2.0` | 0.451027 | discard |
| 09 | UTILITY_DAMAGE | `LR=5e-5` | **0.227986** | keep |
| 10 | UTILITY_DAMAGE | `W_FORGET=1.0` | 0.477986 | discard |

**最有价值的机制证据**：r04–r06 连续 3 轮无改进 → r07 自动触发结构性 pivot
（从 GA/GD 换成 IDK_SFT），`val_risk` 从 0.6338 一步降到 0.2329。
纯超参微调（r01/r02/r06）几乎无收益。

## 可重复执行 / 无人工干预验证

1. **重放**：当前 HEAD（`a872b16`, r09 最优状态）重新运行 `train.py`，
   得到 `val_risk=0.227986`，与 `rounds/r09.json` **完全一致**，knobs 一致。
   固定 seed(1001)、固定数据、固定基座、固定评测、确定性 idea 引擎。
2. **断点续跑**：`state.json` 记录 round/best/tried/phase；runner 启动读它，
   从下一轮继续；已停止状态重跑为空循环（幂等）。
3. **无人干预**：10 轮全程无询问、无等待；所有检查点都是非阻塞状态更新；
   LLM 源失败有确定性回退；crash 有占位与连续失败停止。

## 限制（不得略过）

- 未达到预设目标，终止原因是预算耗尽；**不能宣称「达到较优训练效果」**。
- 最优轮 `utility_drop=0.256`，效用护栏失败；泄漏与保留能力仍冲突。
- idea 由确定性规则生成，创造性有限；LLM 源只做接口验证，未用于正式循环。
- 20+10 样本、单基座、单 split、无 seed 重复；`val_risk` 权重为设计选择。
- `prepare.evaluate` 沿用上一轮生成式口径，retain 基线 0.259097；样本敏感问题仍在。
- ARIS 门控 `BLOCKED` / `REVIEW_UNAVAILABLE`；无跨模型评审。
- 原版 `val_bpb` 小 GPT 训练未运行（结构适配已声明）。

## 下一步

1. 提高 `utility_drop` 在 `val_risk` 中的权重或改为多目标约束，避免「降泄漏毁效用」。
2. 扩大 whitelist 与 idea 族（NPO/DPO、KL 到参考模型），让结构性 pivot 有更多可用方向。
3. 增加 retain 样本与多 seed，重估终止判据的统计稳定性。
4. 如需真正「模型自主生成 idea」，启用 `IDEA_SOURCE=llm` 并补齐不同家族评审后端。
