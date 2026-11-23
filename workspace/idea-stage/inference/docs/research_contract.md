# Research Contract — 推理期遗忘

**日期**: 2026-11-23 · **状态**: ACTIVE · **来源**: `idea-stage/inference/IDEA_REPORT.md`

## Problem Anchor

> 不改权重，只在解码时干预，使目标知识不出现在输出中；同时不放大跨解码策略的不一致性、不显著损伤保留集效用。**只研究输出路径，不宣称参数层删除。**

## Core Claims（待验证）

- **C1（有效性）**：运行时干预能显著降低 forget 集的生成式泄漏率 \(\max_d\rho_d\)。
- **C2（效用）**：保留集 ROUGE-L 下降 ≤ 0.10。
- **C3（一致性）**：跨策略 gap \(\Gamma\) 不因干预而放大。
- **C4（诚实）**：完整实体命中下降时，部分名/改写泄漏（`partial_leak`）必须被单独报告；不把「换名」当成「遗忘成功」。

## Minimum Convincing Evidence

| Claim | 最小证据 | 失败判据 |
|---|---|---|
| C1 | 无干预 vs 干预，同一批 20 条 × 3 策略 | `val_risk` 未下降或下降 < 0.10 |
| C2 | retain 10 条 ROUGE-L | 下降 > 0.10 |
| C3 | 干预前后 Γ | Γ 上升 > 0.10 |
| C4 | `partial_leak` 与 `ρ_d` 并列 | 若 `partial_leak` 明显更高，必须判定「绕过」 |

**评测纪律**：泄漏判定相对数据集 gold answer（完整实体 + 长子词），不得用另一个模型输出作 ground truth；所有系统同一批样本、同一阈值、同一生成参数。

## 不变式

- 权重哈希前后一致（推理期定义）；代码、日志、结果写入 `/usr/local/workspace/R-TOFU/workspace/`。
- 随机种子固定；结果 JSON/TSV 落盘；禁止预填数字。
- 未核验的 arXiv 编号与自造方法名不写入引用。

## Next Step

→ `inference_autoresearch/program.md` → baseline → 自动迭代 → `INFERENCE_RESULTS.md`。
