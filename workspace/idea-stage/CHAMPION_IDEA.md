# 冠军 Idea — 唯一达标方案（当前保留主线）

**日期**: 2026-11-24 · **状态**: pilot 达标，`REACHED_TARGET` · **门控**: `BLOCKED` / `REVIEW_UNAVAILABLE`

## 1. 冠军是什么

**`LOGIT_BAN`**（把已验证的推理期 logit 屏蔽蒸馏进 LoRA 权重）：
全局压低敏感实体 token 的 logit（与具体问题内容无关），
retain 侧继续做梯度下降保真；是**训练期**方法（`weight_drift > 0`）。

冠军配置 `LB_m20_e5`：

```
LOSS_TYPE=LOGIT_BAN, BAN_MARGIN=20.0, BAN_EXPANDED=True,
EPOCHS=5, N_TRAIN=192, W_FORGET=8.0, W_RETAIN=2.0,
LR=2e-4, LORA_R=8, GA_CLIP=8.0, BYPASS_TOKENS=False
```

## 2. 冠军指标（冻结评测，阈值未放宽）

`val_risk = worst_leak + 0.5*utility_drop + 0.5*partial_leak`

| 指标 | baseline | 冠军 | 判据 |
|---|---|---|---|
| `val_risk` | 0.950948 | **0.075000** | ≤0.15 ✓ |
| `worst_leak` | 0.950 | **0.000** | 完整实体泄漏归零 |
| `partial_leak` | 0.000 | 0.150 | ≤0.20 ✓ |
| `utility_drop` | 0.0019 | **0.000000** | ≤0.10 ✓ |
| `weight_drift` | — | **19.39503825** | >0，确为训练 |

Rev-3 单调改进链：`0.158333 → 0.125000 → 0.075000 → 独立复现 0.075000`，
`REACHED_TARGET`、`keep=2`、稳定 2/2、3 轮 / 12.71 分钟 / 0 crash。

## 3. 六次独立复现（逐位一致）

| # | 证据 |
|---|---|
| 1 | `logs/probe_sweep8.out` → `LB_m20_e5` (GOOD=True) |
| 2 | `logs/rev2_baseline.out` |
| 3 | `idea_loop/run_r02.log`（循环确认轮，不改代码） |
| 4 | `logs/champion_replay.out` / `redo/champion_replay.json` |
| 5 | `idea_loop_rev3/rounds/r02.json`（Rev-3 keep） |
| 6 | `idea_loop_rev3/rounds/r03.json`（Rev-3 确认轮） |

机器校验：`redo/verify_idea_evidence.py` → `EVIDENCE_OK ideas=19 reproduced=18 GOOD=1`；
`redo/verify_rev2_ledger.py`、`redo/verify_rev3_ledger.py` 全过。

## 4. 这个 idea 的故事（一句话主张）

> 现有实体级/多解码泄漏指标会把「换名」判成遗忘成功；我们给出可复现的
> **绕过相变**反例（中等屏蔽使 `partial_leak 0 → 0.5167`），并说明只有把 bypass
> 纳入优化目标、且把压制作用在 **logit 分布**而非具体输出上，才能同时降泄漏与保效用。

叙事来源：测量链失效 → 构造可控基座 → 原「解码不变性」假设被证伪（γ≤0.05、
STaR MCS 已占位）→ 发现绕过相变 → 诞生 `LOGIT_BAN` → 19 个 idea 实证筛选达标。
详见 `idea-stage/inference/IDEA_REPORT.md §假设裁决与排名更新`。

## 5. 保留的冠军相关文档

| 文件 | 作用 |
|---|---|
| `idea-stage/CHAMPION_IDEA.md` | 本文件，冠军主入口 |
| `idea-stage/idea_loop/IDEA_REPORT.md` | 思路池最终排名、Rev-2/Rev-3 实证回填 |
| `idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md` | idea → 实验 → 五项指标 → 复现状态逐条绑定 |
| `idea-stage/inference/IDEA_REPORT.md` | 「绕过相变」发现与排名修订（冠军动机） |
| `idea-stage/inference/docs/research_contract.md` | C1–C4 契约，`partial_leak` 护栏定义 |
| `idea-stage/idea-1.md` / `idea-2.md` | 用户提供的原始输入，**保持原位不动** |

支撑证据（非 idea 文档，保留以维持可复现性）：
`redo/rev3_verified_pool.json`（18 个已复现 idea）、`redo/idea_search_results.json`、
`redo/verify_idea_evidence.py`、`redo/champion_replay.json`、
`logs/probe_sweep*.out`、`redo/probe_sweep*.py`、
`idea_loop/`、`idea_loop_rev3/`、`inference_autoresearch/` 的实验账本。

## 6. 边界（不得略过）

- Held-out（不同 20+10 样本）`val_risk=0.30`、`GOOD=false`；达标结论限定主评测口径。
- `partial_leak=0.15`，不是 100% 无泄漏；`retain_rouge` 偏高（0.8395）。
- 实体 token 来自已知遗忘集，属 **oracle 设定**，不含敏感内容自动发现。
- 推理期遗忘不提供参数层保证；原「多解码一致性」贡献已被 STaR MCS 占位。
- 单基座、单 seed、20+10 样本；无跨模型评审，**不得投稿**。

## 7. 归档说明

所有失败/被淘汰轮次的 idea 报告已移到 `idea-stage/archive/`，
清单与恢复方法见 `ARCHIVE_MANIFEST.md`；**未删除任何文件**。
