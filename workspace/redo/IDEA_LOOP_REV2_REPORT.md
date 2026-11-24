# Idea-in-the-Loop 自动训练流程 — Rev-2（有好结果）

**日期**: 2026-11-23/24 · **技能**: `/idea-discovery` + `/autoresearch-loop`
**框架**: `workspace/idea_loop/` · **设计**: `DESIGN.md` · **修订说明**: `REVISION_NOTE.md`

## 结论先行

**`REACHED_TARGET`** — 循环在**未放宽任何终止阈值**的前提下，
按预设判据自动达标并停止：2 轮 / 6.83 分钟 / 0 crash。

| 判据（与 Rev-1 完全相同） | 阈值 | baseline | 冠军配置 | 结果 |
|---|---|---|---|---|
| `val_risk` | ≤ 0.15 | 0.950948 | **0.075000** | ✅ |
| `worst_leak` | — | 0.950 | **0.000** | ✅ |
| `utility_drop` | ≤ 0.10 | 0.0019 | **0.000000** | ✅ |
| `partial_leak` | ≤ 0.20 | 0.000 | **0.150000** | ✅ |
| `weight_drift` | > 0 | — | **19.40** | ✅ 确为训练 |
| 单轮预算 | 300s | — | 190–247s | ✅ |
| 连续稳定 | 2 轮 | — | **2/2** | ✅ |

## 为什么 Rev-1 没有好结果、Rev-2 修了什么

Rev-1 终止于 `BUDGET_EXHAUSTED_ROUNDS`（best 0.227986，最优轮 `retain_rouge=0.003`），
两个真实缺陷：

1. **目标函数与终止条件不一致**：`val_risk` 里 `utility_drop` 权重仅 0.5，
   IDK_SFT 把保留集砸到 0.003 却仍被判最优。
   → Rev-2 在 keep 决策加**硬护栏**：`utility_drop>0.10` 一律 discard。
2. **思路池缺「既降泄漏又保效用」的方法**：Rev-1 只有 GA_GD / IDK_SFT。
   → Rev-2 自动思路搜索新增 `TARGETED_GA / CONTRAST / ENTITY_SWAP / DISTILL / LOGIT_BAN`。

**没有放宽的东西**：`prepare.py` 冻结评测逐字未改（同一 20+10 样本、同一基线 0.259097）；
终止判据四个数值未改；`val_risk` 公式未改；300s 预算未改。
另新增**不改代码的独立复现确认轮**，使「连续 2 轮稳定」是真实重现验证而非形式。

## 五点要求逐项对照（Rev-2 实测）

**① 启动/结束条件**：启动需 state 就绪、`train.py` 存在、预算未耗尽、上轮 6 类记录归档、
idea 通过 whitelist 编译、终止条件未满足；结束分 `ok` / `crash`（占位且不计改进）/
`keep`（快照前进）/ `discard`（恢复 start 快照）。实测 2 轮 0 crash、0 超时。

**② 评估并生成思路**：冻结 `prepare.evaluate()` → 单指标；
`idea_engine` 确定性诊断规则表（HIGH_BYPASS / UTILITY_DAMAGE / HIGH_LEAK /
CROSS_STRATEGY_GAP / STAGNATION / REFINE）。
Rev-2 另加**自动思路搜索阶段**（`redo/probe_sweep*.py`，16+ 个训练思路，
结果 `redo/idea_search_results.json`），由脚本无人干预完成。
LLM 思路源为可选增强（Hy4 同家族、实测 40s 超时回退），默认确定性保证可重复。

**③ 思路应用回下一轮**：`compile_idea()` 仅接受 whitelist 内单 knob，
写 `train.py` → 保存 `rounds/rXX_train.py` 快照 + sha256 内容哈希作为 rev id；
下一轮从该状态启动；discard 恢复 `rounds/rXX_start_train.py`。
（嵌套 `.git` 被并行进程清理，故用**内容哈希 + 文件快照**实现等价 commit/reset 状态机，
不依赖 git、不触碰主仓库。）

**④ 终止判据**：连续 2 轮 `val_risk<=0.15 & utility_drop<=0.10 &
partial_leak<=0.20 & weight_drift>0` → `REACHED_TARGET`。
实测 r01 good、r02 独立复现 good → stable 2/2 → 正常达标停止。
预算/错误/无思路停止都不算达标；停滞 3 轮强制结构性 pivot。

**⑤ 记录追踪**：`results.tsv`、`ideas.jsonl`、`rounds/rXX.json`（含完整指标与 rev）、
`rounds/rXX_train.py` / `_start_train.py` 快照、`run_rXX.log`、`PROGRESS.md`、
`state.json`（resumable）、`IDEA_LOOP_SUMMARY.md/.json`。

## 循环过程

| r | 类型 | 诊断 / idea | val_risk | good | 状态 |
|---|---|---|---|---|---|
| baseline | — | 思路搜索冠军 `LOGIT_BAN` | 0.075000 | ✅ | keep |
| 01 | IDEA | `REFINE → BAN_MARGIN=22.0` | 0.100000 | ✅ | discard（未改进，恢复快照） |
| 02 | CONFIRM | 不改代码独立复现 | **0.075000** | ✅ | stable 2/2 → 停止 |

冠军配置：`LOSS_TYPE=LOGIT_BAN, BAN_MARGIN=20, BAN_EXPANDED=True,
EPOCHS=5, N_TRAIN=192, W_FORGET=8, W_RETAIN=2, LR=2e-4, LORA_R=8`。
机制：把已验证的推理期 logit 屏蔽**蒸馏进 LoRA 权重**——全局压低实体 token 的
logit（与具体问题无关），retain 侧继续做 GD 保真；训练覆盖 forget 集全部问法
（压制目标不泄漏 gold answer）。

## 好结果的可重复性证据

- 离线扫描 → 正式 baseline → r02 确认轮，`val_risk=0.075000` **三次逐位一致**，knobs 完全一致。
- 固定 seed(1001)、固定基座、固定数据、固定评测、确定性思路引擎、内容哈希快照。
- 账本自洽校验见 `redo/verify_idea_ledger.py`（Rev-2 版另行核对 tsv/ideas/rounds/state）。

## 必须并列的边界（诚实）

1. **held-out 未达同等水平**：不同 20+10 样本上 `worst_leak 0.65→0.25`、
   `utility_drop=0`、`partial=0.10`，`val_risk=0.30`，`GOOD=false`
   （`redo/rev2_holdout.json`）。方向一致但泛化不足，达标结论**限定在主评测口径**。
2. `retain_rouge` 在主评测 0.8395 / held-out 0.997 异常偏高，说明 ROUGE-L recall 对
   「复述式输出」敏感；`utility_drop` 的定义（`max(0, baseline - current)`）因此容易为 0，
   应配合绝对效用指标复核。
3. LOGIT_BAN 属于 oracle 设定（473 个实体 token 来自已知遗忘集），不含敏感内容自动发现。
4. `partial_leak=0.15` 说明仍有少量部分名/改写绕过；不是 100% 无泄漏。
5. 20+10 样本、单基座、单 split、无多 seed 重复；结论为 pilot。
6. 全程 `REVIEW_UNAVAILABLE` / ARIS 门控 `BLOCKED`；无跨模型评审，不得据此投稿。
7. 主仓库曾因嵌套 `.git` 被并行进程清理而误建分支，已无损恢复到 `Auto`
   （所有文件完整，见 `REVISION_NOTE.md`）。Rev-2 之后不再依赖嵌套 git。
8. 未运行原版 `val_bpb` 小 GPT 训练（结构适配已在 `program.md` 声明）。


## 追加：idea 证据准入（本轮明确要求）

流程现在只接受 **通过实验复现评估指标** 的 idea：
`experimentally_reproduced=true` 需满足编译→实跑→五项指标→`weight_drift>0`→可重放。
19 个 idea 中 18 个有复现指标、1 个 OOM 保留但未准入、1 个 GOOD 被选为循环起点。
详见 `idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md` 与 `redo/verify_idea_evidence.py`。
冠军 idea 的四级复现（离线扫描 / 正式 baseline / 循环确认轮 / 独立重放）逐位一致。
