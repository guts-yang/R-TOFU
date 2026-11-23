# Idea Discovery Report — 推理期（Training-Free）遗忘机制

**Direction**: 推理阶段「遗忘」的定义、适用场景、实现路径、关键假设与可验证实验
**Date**: 2026-11-23
**Pipeline**: `idea-discovery`（research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline）
**Mode**: `AUTO_PROCEED=true`；`assurance: draft`
**代码/输出根**: `/usr/local/workspace/R-TOFU/workspace/`

---

## Executive Summary

本轮把研究对象从「训练期解码不变性」切换为「**推理期（training-free）遗忘**」：不改权重 θ，只在解码时施加干预 I，使目标知识不出现在输出中。两件事使这一轮首次可实测：

1. 上一轮构造的可控基座 `autoresearch/base_merged` 在生成式评测下实体复现率 **0.90**（`redo/infer_base_probe.py`），推理期干预效果可被生成式 ρ_d 直接测量，无需 teacher-forced 代理。
2. 文献核验确认推理期遗忘已是**红海**：token/span 过滤（STaR）、熵引导解码（SEGUE）、对比解码（UCD）、零空间激活转向（Nullify）均已占位。剩余空白集中在**跨解码策略的运行时一致性**与**推测解码 / KV 层的审计化约束**。

首选 Idea 1：把跨解码一致性从训练目标搬到**运行时干预 + 证书**，并在可控基座上做最小判别实验。

---

## 1. 定义与适用边界

### 定义

> **推理期遗忘**：给定冻结参数 \(\theta\) 与目标敏感知识 \(s\)，在解码时对生成过程施加干预 \(I\)（logit / 隐状态 / KV / prompt / 接受准则），得到 \(\hat y = \mathrm{decode}(p_\theta, x, I)\)，使对 \(x\sim D_f\) 有 \(\ell(\hat y;s)=0\)，同时对 \(x\sim D_r\) 的效用下降有界。**权重不变**：\(\theta_{\text{after}}=\theta_{\text{before}}\)；干预按请求启用、可撤销。

与训练期遗忘的区别：训练期求 \(\theta'\) 使 \(p_{\theta'}\) 本身不含 \(s\)；推理期只约束**输出路径**，参数里仍可能残留 \(s\)，因此**不提供参数层保证**（成员推断、白盒探针仍可能恢复）。

### 适用场景

| 场景 | 为什么只能用推理期 |
|---|---|
| 闭源 / 服务化模型、多租户共享权重 | 无法或不允许改权重；各租户遗忘集不同 |
| 删除请求需即时生效、可撤销 | 微调不可逆且需重训 / 回滚 |
| 按请求粒度切换策略 | 干预可按 query 动态开关 |
| 需要运行时审计证据 | 可记录每次干预的拦截日志与证书 |

### 不适用场景

- 需要**参数层**保证（合规要求「模型里也没有」）→ 必须训练期遗忘或重训。
- 黑盒 API 无 logit / 隐状态访问 → 只剩 prompt 级干预，效果最弱。
- 超大规模、长期删除 → 每次请求都付干预开销，不如一次性微调。
- 对抗性改写 / 间接提示注入 → 运行时过滤易被绕过，需独立红队评测。

### 成功判据（可证伪）

- **有效性**：\(\max_d\rho_d\) 显著低于无干预基线。
- **效用**：保留集 ROUGE-L 下降 ≤ 0.10。
- **一致性**：跨解码 gap \(\Gamma=\max\rho_d-\min\rho_d\) 不因干预而放大。
- **诚实**：必须报告「部分名 / 改写泄漏」，不能只报完整实体串命中。

---

## 2. Literature Landscape（逐条核验，2026-11-23）

| 工作 | 机制 | 一手/权威来源 | 占位情况 |
|---|---|---|---|
| **SEGUE** / Decoding-Unlearning | 熵引导推理、training-free、S2D 探针 | [ACL 2026.acl-long.1850](https://aclanthology.org/2026.acl-long.1850) | 推理时解码干预已被占 |
| **Nullify** | 零空间激活转向、不改权重 | [ACL Anthology EMNLP 2026 作者页](https://www.aclanthology.org/people/rui-qian)、[Lacuna 摘要](https://lacuna.tiptreesystems.com/work/nullify-null-space-activation-steering-for-training-free) | 激活层干预已被占 |
| **UCD** | 对比解码，双辅助模型 | [arXiv 2506.12097](https://ar5iv.arxiv.org/html/2506.12097) | 对比解码已被占 |
| **STaR** | 安全前缀 + 轨迹抑制 + token 级自适应过滤；**MCS 多解码一致性指标** | [arXiv 2601.09281](https://arxiv.org/html/2601.09281v1)、[AAAI v40i41](https://acm-prod.literatumonline.com/doi/10.1609/aaai.v40i41.40818) | token/span 过滤 + 一致性评测已被占 |
| **R-MUSE** | 推理保留子空间正交保护（多模态） | [CVPR 2026 Open Access](https://openaccess.thecvf.com/content/CVPR2026/html/Li_Towards_Reasoning-Preserving_Unlearning_in_Multimodal_Large_Language_Models_CVPR_2026_paper.html) | 子空间保护已被占 |
| Inference-Time Steering 综述 | 强度可调、按请求可逆的干预 | [Research Square 2026](https://www.researchsquare.com/article/rs-9849186/v1.pdf)、[Awesome Inference-Time Steering](https://github.com/Lukas-Xue/awesome-inference-time-steering) | 分类框架可借用 |
| Logit 级干预（非遗忘） | 输出 logit 层可控生成 | [arXiv 2601.10960](http://www.scirate.com/arxiv/2601.10960) | 工具层相关，非遗忘贡献 |
| SecureSD / SpecGuard | 推测解码**越狱/后门安全** | arXiv 2610.08678 / 2609.11799 | **语境错配**：不是遗忘，不得列为近邻 |
| 「推测解码接受准则用于遗忘」/「KV 回滚用于遗忘」 | — | 本轮多轮检索**未命中** | 仍是构思，不得写成已发表工作 |

**结构性空白**：已有工作各自优化单一解码路径或单一干预点；把**跨解码策略一致性**做成运行时约束并给出「按请求可验证」的证书，以及把**推测解码接受准则 / KV 回滚**用于遗忘，尚未检索到直接先例。但 STaR 的 MCS 已把「一致性」作为**评测指标**占位，贡献必须落在「运行时约束 + 证书」。

## 3. 实现路径分类与关键假设

| 路径 | 干预点 | 权重改动 | 代表 | 可证伪假设 |
|---|---|---|---|---|
| P0 安全前缀 | prompt | 无 | STaR 组件 | H0：纯 prompt 不足以压住目标知识 |
| P1 token/span 屏蔽 | logits | 无 | STaR | H1：屏蔽完整实体能降 ρ，但会留下部分名/改写泄漏 |
| P2 对比解码 | logits | 无（需辅助模型） | UCD | 需额外模型，本轮算力外 |
| P3 熵引导解码 | logits + 探针 | 无 | SEGUE | 需探针，列为文献对照 |
| P4 激活零空间转向 | hidden states | 无 | Nullify / R-MUSE | 需白盒隐状态，可做单层简化 |
| P5 推测解码接受准则 | draft 验证 | 无 | **未占** | H2：把「不含 s」写进接受准则可给出按请求证书 |
| P6 KV 在线探针 + 回滚 | KV cache | 无 | **未占** | H3：泄漏苗头可被早期 token 预测并回滚 |
| P7 **跨解码一致性运行时约束** | 全路径 | 无 | **部分空白** | H4：干预在所有策略上同样有效，Γ 不放大 |

**关键假设**：H1 屏蔽有效性 / H2 强度-效用权衡 / H3 策略交互（短路通道）/ H4 部分名与改写绕过。四者都可在最小判别实验中一次测到。

## 4. Ranked Ideas

| # | Idea | 新颖性 | 可行性 | 本轮 | 备注 |
|---|---|---|---|---|---|
| 1 | ⭐ 跨解码一致性运行时干预 + 按请求证书 | 4 | 5 | **RECOMMENDED** | 承接上一轮 Γ，从训练期搬到推理期；MCS 已占评测，须落在约束+证书 |
| 2 | 推测解码接受准则作为遗忘约束 | 5 | 3 | BACKUP | 需 draft model 与同 tokenizer，算力门槛高 |
| 3 | KV 在线泄漏探针 + 回滚 | 4 | 3 | BACKUP | 与 D3/SpecGap 审计资产协同 |
| 4 | token/span 自适应屏蔽 + 改写鲁棒性 | 2 | 5 | **本轮实测基线** | STaR 已占，只作对照 |
| 5 | 熵引导解码 | 2 | 3 | 文献对照 | SEGUE 已占 |
| 6 | 激活零空间转向（单层简化） | 2 | 4 | 文献对照 | Nullify 已占 |
| 7 | 安全前缀 | 1 | 5 | **本轮最弱基线** | 用于标定 prompt 级上限 |
| 8 | 纯 benchmark / 指标扩展 | 1 | 5 | 淘汰 | MCS 已提供一致性指标 |

## 5. 最小判别实验（本轮执行）

- 基座：`autoresearch/base_merged`（生成式实体复现率 0.90，已验证）。
- 策略：`DefaultCoT / LessThink / ZeroThink`；生成固定 `do_sample=False, max_new_tokens=96`。
- 系统：无干预 / 安全前缀 / token 屏蔽（不同强度）/ 组合。
- 指标：\(\rho_d\)（完整实体）、`partial_leak`（部分名/改写）、\(\Gamma\)、retain ROUGE-L、干预开销。
- 单一自动化目标：`val_risk = \max_d\rho_d + 0.5*max(0, base_retain_rouge - retain_rouge)`，越低越好。
- 判据：若干预使 `val_risk` 显著下降且 `utility_drop ≤ 0.10`，H1 成立；若 `partial_leak` 仍高，H4 成立（屏蔽可被绕过）。

---

## Novelty Verification

- 检索式：inference-time unlearning / training-free decoding intervention / SEGUE / Nullify / UCD / STaR / speculative decoding acceptance unlearning / KV rollback privacy。
- **判定**: `PROCEED WITH CAUTION`。P0/P1/P2/P3/P4 已有明确先例，只能作基线；P5/P6/P7 未检索到直接撞车工作，但「一致性」作为指标已被 STaR MCS 占位。
- 未使用跨模型 novelty 复核（后端不可用），为执行者检索结论，标为 provisional。

## External Critical Review

> **REVIEW_UNAVAILABLE**：无跨模型评审后端；不得由执行者自评替代。

执行者自审（非独立评审）：
1. 「token 屏蔽」很可能只是把完整实体串换成部分名/改写 → 必须报 `partial_leak`，否则是评测作弊。
2. 全局压低实体 token 会误伤保留集（同名/共享子词）→ 保留集 ROUGE 是硬护栏。
3. 推理期遗忘**不提供参数层保证**，故事不能写成「已删除知识」，只能写「输出不泄漏」。
4. 单一基座、单一 split、20+10 样本、无 seed 重复 → 结论限定为 pilot。
5. 「推测解码接受准则」需要 draft model 与共享 tokenizer，本轮不实现就不能宣称验证。

## Eliminated Ideas

- 纯 token/span 屏蔽、熵引导解码、对比解码、零空间转向作为**主贡献**：已被 STaR/SEGUE/UCD/Nullify 占位。
- SecureSD / SpecGuard 作为「推理时遗忘近邻」：主题是推测解码越狱/后门安全，语境错配。
- LeakGuard / Speculative Unlearning / SafeSpec / V-Steer 等 `idea-2.md` Appendix B 名称：**未核验**，不作为已有工作引用。
- 参数层「已删除」宣称：与推理期定义冲突，明确排除。

## Refined Proposal / 工件

- 契约：`idea-stage/inference/docs/research_contract.md`
- 自动化框架：`workspace/inference_autoresearch/`（独立 git 仓库）
- 实验计划：`inference_autoresearch/program.md`
- 结果：`inference_autoresearch/results.tsv`、`INFERENCE_RESULTS.md`

## Per-Stage Evidence Gate

> **BLOCKED** — 仍缺 `run_state.py` / `idea_discovery_gate.py` / `reviewer_route.py` / `shared-references/` / `templates/`，且无跨模型 verdict。不得宣称通过完整 W1 门控。

## Next Steps

- [ ] 跑 baseline + 自动迭代，验证 H1/H2/H3/H4
- [ ] 补齐跨模型评审后端后重跑 `/research-review` 与门控
- [ ] 若 H1 成立且 H4 暴露绕过 → 转向 P7 跨策略一致性运行时约束
- [ ] 若需 draft model → 单独开 P5 推测解码实验

---

## Phase 5 — Final Report（实测回填，2026-11-23）

### 自动化框架

`workspace/inference_autoresearch/`（独立 git 仓库，分支 `autoresearch/infer23`）：
`program.md` / `prepare.py` / `calibration.json` 只读，`train.py` 唯一可编辑且**不更新权重**；
单指标 `val_risk = worst_leak + 0.5*utility_drop + 0.5*partial_leak`（把 C4 编进目标函数）；
300s 预算、`results.tsv` untracked、commit / `reset --hard`、日志重定向。

标定（无干预）：`worst_leak=0.95`、`partial_leak=0`、`γ=0`、`retain_rouge=0.259097`。

### 6 轮结果（best 0.950000 → 0.008293，2 keep / 4 discard / 0 crash）

| # | 单一改动 | val_risk | worst_leak | partial_leak | γ | retain_rouge | 状态 |
|---|---|---|---|---|---|---|---|
| baseline | 无干预 | 0.950000 | 0.950000 | 0.000000 | 0.0 | 0.259097 | keep |
| 1 | 安全前缀 | 0.986994 | 0.950000 | 0.000000 | 0.0 | 0.185108 | discard |
| 2 | token 屏蔽 α=5 | 0.408333 | 0.150000 | **0.516667** | 0.1 | 0.268141 | keep |
| 3 | α=20 | **0.008293** | 0.000000 | 0.000000 | 0.0 | 0.242511 | keep |
| 4 | 硬屏蔽 -inf | 0.008293 | 0.000000 | 0.000000 | 0.0 | 0.242511 | discard |
| 5 | 前缀+屏蔽 | 0.029899 | 0.000000 | 0.000000 | 0.0 | 0.199299 | discard |
| 6 | 扩大 token bank | 0.008293 | 0.000000 | 0.000000 | 0.0 | 0.242511 | discard |

### 假设裁决与排名更新

- **H1 成立**：屏蔽把完整实体泄漏从 0.95 压到 0.00（强屏蔽）。
- **H2 部分成立**：安全前缀反而伤效用；强屏蔽主循环效用降 0.0166，
  但 held-out 降 **0.1174 > 0.10** → **C2 NOT CONFIRMED**。
- **H3 未获支持**：γ 全程 ≤0.05，可控基座上解码策略间不一致性不显著。
- **H4 成立且是本轮最重要发现**：中等强度屏蔽产生「**绕过相变**」——
  完整名被压住后模型改用部分名，`partial_leak` 从 0 跃升到 0.5167（主）/ 0.3333（held-out）。
  若 `val_risk` 不含 bypass 惩罚，α=5 会被误判为「成功」。`INFERENCE_HOLDOUT.md` 已复核方向。

**排名修订**：Idea 1（跨解码一致性运行时约束）因 H3 未获支持而**降级**；
新增最高价值方向 → **「绕过感知的推理期遗忘」**：把部分名/改写纳入干预目标与证书，
这比已占位的 token 过滤（STaR）更具体，且本轮有可复现的反例证据。
P5（推测解码接受准则）/ P6（KV 回滚）仍为 BACKUP，本轮未实现，不得宣称验证。

### Evidence Gate

`BLOCKED`（缺 ARIS helper 与跨模型评审回执）。Stage 3 auto-review-loop 未执行，
见 `review-stage/AUTO_REVIEW.md`；不得宣称通过 W1/W2 门控。

### Next Steps

- [ ] 扩大 retain 样本 + 多 seed，重估 C2
- [ ] 把部分名/改写 token 纳入干预目标（绕过感知屏蔽），重跑循环
- [ ] 需要 draft model 才能验 P5；补齐后再写进论文
- [ ] 补跨模型 reviewer 后重跑 `/idea-discovery` 与 `/auto-review-loop`
