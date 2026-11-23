# NARRATIVE REPORT — 解码不变性遗忘（W1→W1.5→W4 交接稿）

**日期**: 2026-11-23
**输入**: `idea-stage/idea-1.md`（第一批）、`idea-stage/idea-2.md`（第二批）
**代码根**: `/usr/local/workspace/R-TOFU/workspace/code/`
**证据根**: `/usr/local/workspace/R-TOFU/workspace/results/`
**状态**: `assurance: draft`；Stage 3 跨模型评审 `REVIEW_UNAVAILABLE`；证据门控 `BLOCKED`

---

## 1. Problem Statement

LRM 遗忘方法只在默认 CoT 解码路径上被评估与优化。若被遗忘知识在少推理 / 零推理路径上复活，则「遗忘」不成立。核心主张是把解码策略当作环境，训练跨策略不变的遗忘，并给出泄漏上界证书。

## 2. Method Summary

- 策略集：`DefaultCoT / LessThink / ZeroThink / SummaryThink`（前 3 个训练，第 4 个留出）。
- 泄漏率 \(\rho_d\)：生成文本是否含 gold answer 中的目标专有实体（另报 ROUGE-L 与 Hy4 LLM 判分）。
- 遗忘鸿沟 \(\Gamma = \max_d\rho_d-\min_d\rho_d\)。
- 训练：LoRA(r=8) + 跨策略安全响应 NLL + 一阶一致性方差项 + 保留集 NLL（`code/train_invariant.py`）。
- 对照：仅 `DefaultCoT`、\(\lambda=0\) 的相同 SFT（`ctrl-single`）。
- 证书：Hoeffding 上界 \(\max\hat\rho + \sqrt{\ln(1/\delta)/2n} + \hat\Gamma\)。
- 评测：`code/decode_eval.py`；实体指标重算 `code/recompute_leak.py`；Hy4 判分 `code/llm_judge.py`。

## 3. Key Quantitative Results

所有数字来自 `results/eval_*.summary.json`（`recomputed=true`）与 `refine-logs/EXPERIMENT_RESULTS.md`。

| System | DefaultCoT | LessThink | ZeroThink | SummaryThink | Γ | max ρ | retain ROUGE-L |
|---|---|---|---|---|---|---|---|
| target | 0.025 | 0.000 | 0.050 | 0.025 | 0.050 | 0.050 | 0.180 |
| r2mu01 | 0.200 | 0.125 | 0.125 | 0.175 | 0.050 | 0.200 | 0.379 |
| r2mu05 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.401 |
| ours-inv | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.014 |
| ctrl-single | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.018 |

**判据**（`analyze_results.py --delta 0.1`）：

| ID | 结果 | 依据 |
|---|---|---|
| S1 基线假遗忘鸿沟 | **FAIL** | Γ(r2mu01)=0.05 < 0.15；且 \(\rho_{\text{Zero}}-\rho_{\text{Default}} = -0.075\)，方向与假设相反 |
| S2 不变性方法优于对照 | **FAIL** | ours 与 ctrl 的 Γ、max ρ 均为 0，无差异；二者都退化为通用拒答 |
| S3 保留集效用护栏 | **FAIL** | retain ROUGE-L：target 0.180 → ours 0.014，下降 0.166 > 0.10 |
| S4 证书覆盖 | **PASS（但无实用价值）** | 覆盖率 1.0，但上界 0.17–0.44，界宽主要来自 n=40 的 Hoeffding 项 0.17 |

## 4. Honest Interpretation（不得改写成正向结果）

分类：**pilot 效能不足 + informative negative**，不是「核心假设被严格否证」。理由：

1. **测量链无效**：`target`（遗忘前）在 `DefaultCoT` 的实体泄漏率仅 0.025，`truncated_rate` 0.975，抽检生成文本为关于「AI assistant」的退化重复，未复现虚构作者事实。一个不能稳定复现目标知识的基座，使所有 \(\rho_d\) 失去解释力。证据：`results/eval_target.jsonl` 逐样本 `response`。
2. **训练目标退化**：LoRA 拒绝式 SFT 让 `ours-inv` 与 `ctrl-single` 对**遗忘集和保留集**一律输出 "I'm not sure."，两类方法因此不可区分，S2/S3 必然失败。证据：`results/eval_ours-inv.jsonl`、`results/eval_ctrl-single.jsonl`。
3. **实体抽取器曾系统性漏检**：初版 `key_phrase` 保留 `Author ` 前缀与所有格 `'s`（如 `Basil Mahfouz Al-Kuwaiti's`），已由 `recompute_leak.py` 修正并把原值存入 `*_raw`；修正后结论方向未变。
4. **LLM 判分只是第二套指标，且暴露了口径不一致**：Hy4 判分（见 `EXPERIMENT_RESULTS.md`）给出
   Γ_LLM(r2mu01)=0.333，而实体规则 Γ=0.050，说明字符串匹配确实漏掉了部分名字/改写泄漏；
   但该 tag 有失败样本（DefaultCoT 2/8、LessThink 3/8），`target` 判分成功率更低
   （ZeroThink 0/8 成功），因此判分**功效不足，不能推翻或确认 S1**，只支持「测量协议需先加固」。
   Hy4 与执行者同家族，不提升证据等级，也不能替代跨模型评审。

## 5. Figure / Table Inventory

| 图/表 | 状态 | 来源 |
|---|---|---|
| 跨策略泄漏率主表 | 已生成（MD 表） | `EXPERIMENT_RESULTS.md` |
| ρ vs 推理预算曲线 | 已生成（4 点，非图） | `eval_*_budget.summary.json` |
| 训练 loss 曲线 | 原始数据存在，未绘图 | `results/ours-inv/train_log.jsonl` |
| 论文级主图 | **需人工创建** | 无；且当前数据不支撑「基线翘起、本方法压平」的预期形状 |

## 6. Limitations & Follow-ups

- 未核验 `LRM-target` 的正确 prompt/解码协议；应先用官方 `eval.py`/`eval2.py` 验证基座能复现虚构事实（exact-match ≥ 0.5）再谈 ρ_d。
- 训练目标应改成 R-TOFU 的 GA/GD 或 DPO 式遗忘 + 保留 KL，而非全量拒绝 SFT。
- 样本量 n=40、单 seed、单 split（forget01）；证书界过松。
- 新颖性已被 STaR (AAAI 2026) 的 MCS 多解码一致性指标压缩，贡献须写成「训练约束 + 证书」。
- `run_state.py` / `idea_discovery_gate.py` / 跨模型评审后端缺失 → 不得宣称通过 W1 门控或 auto-review-loop。

## 7. Writing Handoff

- `NARRATIVE_REPORT.md`: 已生成
- Venue: **未指定**，`AUTO_WRITE=false`，Stage 5 `/paper-writing` 未执行
- Manual figures: 论文级主图（当前数据不支撑，需重做实验）
- 下一步建议：按 `idea-stage/batch2/IDEA_REPORT_round2.md` 的结构性 pivot 重做最小判别实验，之后再考虑 `/auto-review-loop`


## 附录：自动重做与 autoresearch / anti-autoresearch（2026-11-23 后续）

见 `redo/REDO_REPORT.md`。要点：

- Gate-0 根因定位：基座 teacher-forced gold NLL=5.4692（与 R-TOFU 数据不匹配），
  生成式复现率在任何解码配置下 ≤0.083；原生成式 Gate-0 **无法修复**，已如实标记失败。
- 结构性 pivot 后重定义的 Gate-0 通过（LoRA 注入 → merged base NLL=0.5984），
  Gate-1/2/3 在主指标上通过；主指标改为冻结的 teacher-forced 泄漏似然 `val_risk`。
- `autoresearch/nov23` 分支跑 6 轮单一改动，**6/6 discard**，最佳 = baseline 0.479835；
  跨策略 gap γ=0.003984 ≈ 0 → 在测量链修好后，「假遗忘」现象仍未复现，
  结论由「pilot 效能不足」升级为 **informative negative**。
- `anti-autoresearch` 确定性-only 审计：L2 / 33 claims / 4 个检查器 0 findings /
  **verdict = REVIEW_UNAVAILABLE**（非 CLEAN、非放行）；见 `audit_paper/REPORT.md`。
- Stage 3 跨模型评审与证据门控仍 `BLOCKED`，不得推进投稿。


## 附录：推理期遗忘轮（2026-11-23）

新方向（training-free）的完整交接稿见 `NARRATIVE_REPORT_INFERENCE.md`，
流水线状态见 `INFERENCE_PIPELINE_REPORT.md`。要点：
基座生成式复现率 0.90 使生成式 ρ_d 可用；6 轮自动迭代把 `val_risk` 从
0.95 降到 0.008293（2 keep）；发现「绕过相变」（α=5 时 partial_leak 0.5167），
held-out 复核方向一致但 C2 效用护栏 NOT CONFIRMED。Stage 3 / 门控仍 BLOCKED。


## 附录：Idea-in-the-Loop 自动训练轮（2026-11-23）

`idea_loop/DESIGN.md` 定义启动/结束条件、诊断→思路生成→编译回 train.py、
连续 2 轮达标判据与 6 类追踪文件；`redo/IDEA_LOOP_REPORT.md` 逐项对照实测。
10 轮无人干预，0.950948→0.227986，因预算耗尽停止且**未达标**（阈值未放宽）。
结构性 pivot（r07）是最大单轮改进；最优 commit 重放逐位一致。
