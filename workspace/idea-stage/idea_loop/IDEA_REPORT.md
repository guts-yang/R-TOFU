# Idea Discovery Report — 训练思路的自主优化（Idea-in-the-Loop）

**Direction**: 设计一个能自主训练、评估、生成优化思路、应用思路并循环迭代直至达标的自动化研究流程
**Date**: 2026-11-23
**Pipeline**: `/idea-discovery` + `/autoresearch-loop`
**Mode**: `AUTO_PROCEED=true`；`assurance: draft`
**框架**: `workspace/idea_loop/` · **实测**: `redo/IDEA_LOOP_REPORT.md`

---

## Executive Summary

本轮把 `idea-discovery` 的「生成 idea → 验证 → 重排」**压进每一轮训练**，
形成双层状态机：外层按当前结果诊断并生成一个 whitelisted idea，
内层按 autoresearch 硬约束（单文件可编辑 / 300s / 单指标 / commit-reset）实测它。
框架已无人工干预跑满 10 轮（7.97 分钟，4 keep / 6 discard / 0 crash），
`val_risk` 从 `0.950948` 降到 `0.227986`，但**未达到预设目标 0.15**，
终止原因 `BUDGET_EXHAUSTED_ROUNDS`，如实记录。

最有价值的发现是**结构性 pivot 的价值**：连续 3 轮超参微调无改进后，
第 7 轮自动把训练目标从 GA/GD 换成 IDK_SFT，`val_risk` 一步从 0.6338 降到 0.2329。

## Literature Landscape

本轮是**流程/机制设计**，不是文献查新；不生成 BibTeX、不虚构条目。
可对照的已核验来源：

| 概念 | 来源 | 关系 |
|---|---|---|
| autoresearch 单指标循环 | `autoresearch-loop` 技能（guts-yang/autoresearch 快照） | 提供内层状态机 |
| 思路生成/重排 | `idea-discovery` 技能（ARIS W1） | 提供外层 idea 循环 |
| 停滞时结构变化 | autoresearch `program.md` 的「更激进架构变化」 | 本轮实现为固定优先级 pivot |
| Hy4 端点 | `/usr/local/workspace/.env` | 可选 idea 生成器；**同家族，不是评审** |

## Ranked Ideas（按实测效果，不是纸面评分）

10 轮产生的 idea 全部来自确定性诊断规则表，按对 `val_risk` 的实际贡献排序：

| # | 诊断 | idea | val_risk | 状态 | 评价 |
|---|---|---|---|---|---|
| 1 | UTILITY_DAMAGE | `LR=5e-5` | **0.227986** | keep | 全局最优；但 utility_drop 0.256 未过护栏 |
| 2 | **STAGNATION** | `LOSS_TYPE="IDK_SFT"` | 0.232897 | keep | **单轮最大改进**；结构性 pivot 有效 |
| 3 | HIGH_LEAK | `EPOCHS=2` | 0.633786 | keep | 增大训练量有实质收益 |
| 4 | HIGH_LEAK | `W_FORGET=2.0` | 0.950000 | keep | 仅微弱改进 |
| 5 | HIGH_LEAK | `GA_CLIP=12.0` | 0.633786 | discard | 与当前最优持平，按简单性准则丢弃 |
| 6 | HIGH_BYPASS | `BYPASS_TOKENS=True` | 0.683333 | discard | 方向正确但本轮未改进 |
| 7 | UTILITY_DAMAGE | `W_RETAIN=2.0` | 0.451027 | discard | 效用侧尝试失败 |
| 8 | UTILITY_DAMAGE | `W_FORGET=1.0` | 0.477986 | discard | 回退式尝试失败 |
| 9 | HIGH_BYPASS | `W_FORGET=0.5` | 0.916667 | discard | 减弱压力反而更差 |
| 10 | HIGH_LEAK | `W_FORGET=4.0` | 1.008333 | discard | 过强导致指标恶化 |

**排名修订**：与「调超参」相比，**切换训练目标/idea 族**是收益最高的一类；
下一轮 idea 池应优先扩充 `LOSS_TYPE` 候选（NPO/DPO、KL 正则），
而不是继续扫 `W_FORGET` / `GA_CLIP`。

## Novelty Verification

`NOT_APPLICABLE`（本轮产出是流程机制，不是学术新颖性主张）。
不宣称方法新颖；只报告机制在本可控环境中的实测行为。
未做全文级查新，未使用跨模型 novelty 复核。

## External Critical Review

> **REVIEW_UNAVAILABLE**：无跨模型评审后端；不得由执行者自评替代。

执行者自审（非独立评审）：
1. 默认 idea 源是**确定性规则**，创造性有限；「模型自主生成思路」这一表述需限定为
   「系统按诊断规则生成思路，LLM 为可选增强」。
2. LLM 源单次验证因 Hy4 40s 超时回退（`logs/idea_llm_probe.out`），
   说明降级机制有效，但**本环境 LLM 源不可用**，不得写成已启用。
3. 最优轮的 `utility_drop=0.256 > 0.10`，终止判据正确地没有放行；
   但 `val_risk` 中效用权重仅 0.5，仍把该轮判为 best → 目标函数设计需改进。
4. 20+10 样本、单 seed、单基座；结论限定为 pilot。
5. 未达标是真实结果，不得改写阈值或删轮次来制造「达标」。

## Eliminated Ideas

- 继续增大 `W_FORGET`（4.0）→ 指标恶化，已从候选剔除。
- 认为「val_risk 最低即达标」→ 被效用护栏否证。
- 把 Hy4 当独立评审或门控回执 → 同家族，明确排除。
- 权重接续式训练（每轮接着上轮权重）→ 为可重复性改用固定基座 + 代码状态继承。

## Refined Proposal / 工件

- 流程设计：`idea_loop/DESIGN.md`（用户 5 点逐项定义）
- 组织代码：`idea_loop/program.md`（只读）
- 冻结评测 / 思路引擎：`idea_loop/prepare.py`、`idea_loop/idea_engine.py`
- 唯一可编辑：`idea_loop/train.py`
- 账本：`results.tsv` / `ideas.jsonl` / `rounds/rXX.json` / `state.json` / `PROGRESS.md`
- 汇总：`idea_loop/IDEA_LOOP_SUMMARY.md`、`redo/IDEA_LOOP_REPORT.md`

## Per-Stage Evidence Gate

`BLOCKED` — 仍缺 `run_state.py` / `idea_discovery_gate.py` / `reviewer_route.py`
与跨模型 verdict。本轮是执行者自研机制，不宣称通过 W1 门控。

## Next Steps

- [ ] 提高效用护栏权重或改多目标约束，避免「降泄漏毁效用」被判为最优
- [ ] 扩充 `LOSS_TYPE` 候选族（NPO / DPO / KL），让结构性 pivot 有更多方向
- [ ] 增大 retain 样本 + 多 seed，重估终止判据统计稳定性
- [ ] 补齐不同家族 LLM 后端后再启用 `IDEA_SOURCE=llm`
- [ ] 补齐 ARIS helper 与评审后端后重跑门控

---

## Phase 5 追加：Rev-2 实证回填（有好结果，2026-11-24）

**`REACHED_TARGET`**：在**未放宽任何阈值**的前提下，循环 2 轮 / 6.83 分钟达标停止。
`val_risk 0.950948 → 0.075000`，`worst_leak 0.95 → 0.00`，
`utility_drop=0`，`partial_leak=0.15`，`weight_drift=19.4>0`，稳定计数 2/2。

### 思路池最终排名（按实证贡献重排）

| # | 思路 | 结果 | 判定 |
|---|---|---|---|
| 1 | ⭐ **LOGIT_BAN**（把推理期 logit 屏蔽蒸馏进权重） | `val_risk=0.075` 全部护栏通过 | **唯一达标**，冠军 |
| 2 | `BAN_MARGIN=22.0`（REFINE 微调） | `0.100` good 但未改进 | discard |
| 3 | `LOGIT_BAN margin=30 / e4` | `0.125`，worst=0，partial=0.25 | 差一点 |
| 4 | `CONTRAST` e3 | `0.525`，utility=0，泄漏 0.35 | 保效用但不达标 |
| 5 | `DISTILL` / `ENTITY_SWAP` / `TARGETED_GA` | 0.78–0.88 | 泛化不足 |
| 6 | `IDK_SFT`（Rev-1 最优） | `0.228` 但 `utility_drop=0.256` | 被硬护栏否决 |

**修订后的核心结论**：
1. 「降泄漏」与「保效用」的冲突不是靠调超参解决的，
   而是靠**换思路族**：全局 logit 压制（与问题内容无关）才能同时满足两者。
2. 单纯模仿输出（DISTILL/ENTITY_SWAP）泛化不到 held-out 问法；
   压制 logit 分布才泛化。
3. 「绕过相变」依旧存在：完整名被压住后 `partial_leak` 仍 0.15（held-out 0.10）。
4. 目标函数必须与终止条件一致，否则自动化循环会奖励「一律拒答」的退化解。

### Held-out 边界（不隐藏）

不同 20+10 样本：`worst_leak 0.65→0.25`（降 62%）、`utility_drop=0`、
`partial=0.10`，但 `val_risk=0.30`、`GOOD=false`。
**达标结论限定在主评测口径**；泛化不足是下一轮首要问题。见 `redo/rev2_holdout.json`。

### Evidence Gate

仍 `BLOCKED` / `REVIEW_UNAVAILABLE`；无跨模型评审，不得投稿。

---

## 追加：Idea 证据准入（「有通过实验复现评估指标的 idea」）

本轮明确约束：**不接受纸面 idea**。进入正式训练循环的每个 idea 必须
`experimentally_reproduced=true`——编译成 whitelist knob、实跑训练+冻结评估、
产出五项指标、`weight_drift>0`、同配置同 seed 可重放。

权威账本 `idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md`、
机器可读 `redo/idea_search_results.json`、确定性校验 `redo/verify_idea_evidence.py`
（`EVIDENCE_OK ideas=19 reproduced=18 GOOD=1`）。
原始证据是 `logs/probe_sweep*.out` 的脚本 stdout，不是人工填写。

19 个 idea 中 18 个有复现指标、1 个 OOM crash（保留但未准入）、
唯一 GOOD 的 `LB_m20_e5 (val_risk=0.075)` 才被选为循环起点，
并经离线扫描 / 正式 baseline / 循环确认轮 / 独立重放四级逐位一致。

因此 **Phase 5 的排名是实验驱动的，不是评分表驱动的**：
`LOGIT_BAN > CONTRAST > DISTILL > ENTITY_SWAP > IDK_SFT` 的次序
完全由 `worst_leak / partial_leak / utility_drop / weight_drift` 的实测值决定。
`DESIGN.md §9` 与 `program.md` 已把该准入条件固化为只读组织代码。
