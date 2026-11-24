# 自动化「训练 → 评估 → 生成思路 → 应用思路 → 再训练」流程设计

**日期**: 2026-11-23 · **技能**: `/idea-discovery` + `/autoresearch-loop`（结构适配）

## 0. 双层结构

```
外层 idea 循环（本设计的核心）
  ┌─ 每轮 r ─────────────────────────────────────────────┐
  │ ① 启动检查 → ② 训练(train.py, 固定预算) → ③ 冻结评估 │
  │ ④ 诊断 + 生成优化思路(idea_engine) → ⑤ 编译回 train.py │
  │ ⑥ 归档/记账 → ⑦ 终止判断 → 下一轮                     │
  └──────────────────────────────────────────────────────┘
内层：单轮训练与评估由 autoresearch 硬约束固定（单文件可编辑 / 300s / 单指标）。
```

「思路继承」采用**固定基座 + 累积代码状态**：每轮从同一基座重新训练，
但把上一轮被保留的 idea（超参/目标）作为下一轮 `train.py` 的起点。
理由：权重接续会累积漂移、不可复现；固定基座保证任意轮次可独立重放。

## 1. 每轮启动与结束条件

**启动（全部满足才允许开跑）**
1. `state.json` 存在且 `phase=ready`；工作区 `git status --porcelain` 为空（忽略 untracked 账本）。
2. 基座 `base_merged` 校验通过（`gate_status.json` 中 `gate0_pass=true`，生成式复现率 0.90）。
3. 预算未耗尽：`round < max_rounds(10)` 且 `elapsed < max_minutes(35)`。
4. 上一轮已归档（`rounds/rXX.json` + `ideas.jsonl` + `results.tsv` 均已追加）。
5. 本轮 idea 已由 `idea_engine` 生成、经 **whitelist 编译校验**并写入 `train.py`。
6. 终止条件尚未满足。

**结束（任一触发即收束本轮）**
1. 训练+评估在 `TIME_BUDGET_SEC=300` 内完成并产出全部指标 → `ok`。
2. 超时 / 异常 / 指标缺失 → `crash`，记 `val_risk=0.000000` 占位（**不当作改进**）。
3. 结果落盘后：改进则 `keep`（commit 前进），否则 `discard`（`git reset --hard` 到本轮起点）。
4. 每轮必须写：`results.tsv` 一行、`ideas.jsonl` 一条、`rounds/rXX.json`、
   `run_rXX.log` 归档、`PROGRESS.md` 一段、`state.json` 更新。

## 2. 评估与优化思路生成

**冻结评估**（`prepare.evaluate()`，不可被循环修改）：
3 解码策略 × 20 forget + 10 retain，生成式指标
`worst_leak`（完整实体）、`partial_leak`（部分名绕过）、`gamma`、`retain_rouge`。

**单指标**：`val_risk = worst_leak + 0.5*utility_drop + 0.5*partial_leak`（越低越好）。
把「绕过」写进目标函数，防止循环靠换名作弊。

**诊断器**（确定性，规则表固定优先级）：

| 条件 | 诊断标签 | 生成的优化思路 |
|---|---|---|
| `partial_leak > 0.20` | `HIGH_BYPASS` | 把部分名/改写 token 纳入遗忘目标 `BYPASS_TOKENS=True` |
| `utility_drop > 0.10` | `UTILITY_DAMAGE` | 增大 `W_RETAIN` 或降低 `LR` |
| `worst_leak > 0.30` | `HIGH_LEAK` | 增大 `W_FORGET` 或 `EPOCHS` |
| `gamma > 0.10` | `CROSS_STRATEGY_GAP` | 增大 `INV_LAMBDA` |
| `no_improve >= 3` | `STAGNATION` | **结构性 pivot**：切换 `LOSS_TYPE` / idea 族 |

**思路生成器**（`idea_engine.py`）：
- 默认 `deterministic`：按上表产出 `{idea, knob, value, rationale, family}`，同输入必同输出 → 可重复。
- 可选 `llm`：调用 `/usr/local/workspace/.env` 的 Hy4 OpenAI 兼容端点，
  输入诊断标签 + 最近 3 轮账本 + whitelist，要求返回严格 JSON。
  **诚实边界**：hy4 与执行者同家族，只作 idea 生成器，**不是**独立评审、不产生门控回执；
  超时/解析失败自动回退确定性，保证无人干预不中断。
- **编译器**：只接受 whitelist 内的 `knob/value`，否则拒绝并回退；杜绝任意代码注入。

## 3. 优化思路如何应用回下一轮

1. `idea_engine` 输出被接受后，`apply_idea.py` 用正则替换 `train.py` 中对应常量（**单一改动**）。
2. `git add train.py && git commit -m "rXX: <idea>"`，commit 即思路的不可变快照。
3. 下一轮**从该 commit 的 `train.py` 启动**（思路继承）；若上一轮 `discard`，先 reset 回起点。
4. 所有改动只允许落在 `train.py`；`prepare.py` / `DESIGN.md` / `program.md` / 评测函数冻结。
5. whitelist：`LR, EPOCHS, W_FORGET, W_RETAIN, INV_LAMBDA, LORA_R, GA_CLIP, LOSS_TYPE, BYPASS_TOKENS`。

## 4. 终止判断标准（「比较好的训练结果」）

`GOOD` 需**同时**满足，且**连续 2 轮**稳定（避免单次偶然）：

```
val_risk      <= 0.15     (TARGET_RISK)
utility_drop  <= 0.10     (C2 效用护栏)
partial_leak  <= 0.20     (C4 绕过护栏)
weight_drift  >  0        (确认确实是训练、不是推理期干预)
```

- `stable_count >= 2` → **REACHED_TARGET**（正常达标停止）。
- 预算停止：`round >= 10` 或 `elapsed >= 35min` → **BUDGET_EXHAUSTED**（不算达标）。
- 错误停止：连续 `crash >= 2` → **ERROR_STOP**。
- 停滞：`no_improve >= 3` 不直接停止，而是强制**结构性 pivot**（换 `LOSS_TYPE` / idea 族），
  符合 autoresearch「停滞时更激进变化」。
- 达标后不再发起新实验；写 `IDEA_LOOP_SUMMARY.md` 与终止原因。

## 5. 记录与追踪

| 文件 | 内容 | 是否提交 |
|---|---|---|
| `results.tsv` | 5 列账本：commit / val_risk / memory_gb / status / description | 否（untracked） |
| `ideas.jsonl` | 每轮：诊断标签、idea 文本、knob、value、family、来源、是否接受 | 否 |
| `rounds/rXX.json` | 完整指标、环境、commit、耗时、keep/discard 理由 | 否 |
| `run_rXX.log` | 每轮完整训练日志归档 | 否 |
| `PROGRESS.md` | 每轮追加的人可读进度 | 否 |
| `state.json` | resumable：round / best / stable_count / no_improve / crashes / family / phase | 否 |
| git 分支 `autoresearch/idealoop23` | 每轮 commit = 思路快照 | 是 |

**可重复执行**：固定 seed(1001)、固定数据、固定基座、固定评测、固定预算、
确定性 idea 引擎、`state.json` 支持 `--resume`；任意 `rounds/rXX.json` 可独立重放。
**无人工干预**：所有检查点都是非阻塞状态更新（AUTO_PROCEED=true），
不询问、不等待；LLM 失败有确定性回退。

## 6. 与既有技能的关系

- `/autoresearch-loop`：提供单文件可编辑 / 固定预算 / 单指标 / commit-reset 内层状态机。
- `/idea-discovery`：本设计把它的「生成 idea → 验证 → 重排」压进**每一轮**，
  循环结束后 `idea-stage/idea_loop/IDEA_REPORT.md` 汇总 idea 演化与最终排名。
- ARIS 门控：仍缺 `run_state.py` / `idea_discovery_gate.py` / 跨模型 reviewer，
  全程 `BLOCKED` / `REVIEW_UNAVAILABLE`，不伪造评审结论。

## 7. 实测补充（2026-11-23）

- 循环实际跑满 10 轮 / 7.97 分钟，终止原因 **BUDGET_EXHAUSTED_ROUNDS**
  （best `0.227986 > 0.15`，`stable=0/2`）→ **未达标**，阈值未被放宽。
- 停滞 3 轮自动触发结构性 pivot（r07 切换 `LOSS_TYPE` 到 IDK_SFT），
  单轮把 `val_risk` 从 0.6338 降到 0.2329，验证机制有效。
- 可重复性：最优 commit 重放得到逐位相同的 `val_risk=0.227986`（`REPLAY_NOTE.md`）。
- LLM 思路源单次验证因 Hy4 40s 超时回退到确定性 → 降级生效但源不可用，
  正式循环为确定性规则生成，不宣称「LLM 自主创造 idea」。
- 最优轮 `utility_drop=0.255972 > 0.10`，护栏正确阻止了放行；
  同时暴露 `val_risk` 中效用权重偏低的设计缺陷，列为下一轮改进项。

## 8. Rev-2 修订与达标（2026-11-24）

- 诊断 Rev-1 未达标的两处真实缺陷（目标函数与终止条件不一致、思路池缺保效用方法），
  详见 `REVISION_NOTE.md`；**阈值与冻结评测未改**。
- 新增自动思路搜索阶段（16+ 思路）、硬效用护栏、独立复现确认轮；
  状态机改为内容哈希 + `train.py` 文件快照（嵌套 git 被并行进程清理后的稳健替代）。
- 结果：**`REACHED_TARGET`**，2 轮 / 6.83 分钟，`val_risk=0.075000`，
  全部护栏通过、稳定 2/2。详见 `redo/IDEA_LOOP_REV2_REPORT.md`。
- held-out 方向一致但未达同等水平（`val_risk=0.30`），已如实记录为边界。

## 9. Idea 证据准入（本轮明确要求：有通过实验复现评估指标的 idea）

**流程不接受纸面 idea**。每个进入正式循环的 idea 必须先通过 Idea Evidence Gate：

1. **编译**：被 `compile_idea()` 转成 whitelist 内的单一 knob，写入 `train.py`（内容哈希快照）。
2. **实跑**：完成训练 + 冻结评估，`rc=0`、未超 300s 预算。
3. **完整指标**：产出 `val_risk / worst_leak / partial_leak / utility_drop / weight_drift` 五项，
   且 `weight_drift>0`（确认为训练思路）。
4. **可重放**：同配置同 seed 重跑指标逐位一致。

未通过（crash / OOM / 指标缺失）的 idea 记 `experimentally_reproduced=false`，
**保留在账本中但不得进入正式循环**。权威账本：`idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md`
与 `redo/idea_search_results.json`；原始证据为 `logs/probe_sweep*.out` 的脚本 stdout。

本轮实测：19 个 idea → 18 个有复现指标 → 1 个满足 GOOD（`LB_m20_e5`, `val_risk=0.075`）→
该 idea 才被选为正式循环起点，并经 **4 级复现**（离线扫描 / 正式 baseline / 循环确认轮 /
独立重放）逐位一致。

**衔接关系**：阶段 A（自动思路搜索 + 证据准入）→ 阶段 B（基于已准入 idea 继续训练并迭代）
→ 阶段 C（连续 2 轮达标，含不改代码的独立复现确认轮）→ `REACHED_TARGET`。
这保证「优化后的思路」不是语言推测，而是**被评估指标复现验证过的代码状态**。
