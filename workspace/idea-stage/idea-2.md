# Idea Discovery Report — 大推理模型（LRM）机器遗忘创新

**Direction**: 对 LRM（Large Reasoning Model）机器遗忘进行创新
**Date**: 2026-11-23
**Pipeline**: research-lit → idea-creator → novelty-check → research-review → research-refine-pipeline
**Mode**: AUTO_PROCEED=true（非阻塞）；执行到可用环境允许的最大范围

> ⚠️ **执行边界与诚实声明（务必先读）** — 本仓库环境经核查：`torch 2.8.0` 但 `cuda=False`（无 GPU，无法跑真实 LLM pilot）；跨模型评审 MCP（codex/grok/claude/antigravity）**不可用**；状态门控 helper（`run_state.py` / `idea_discovery_gate.py`）**缺失**。因此本报告如实采用降级模式：
> - pilot 信号全部标注 `needs manual pilot`（纸面证据 + 用户既有复现资产为依据，非本机实测）；
> - 两个评审阶段标注 `REVIEW_UNAVAILABLE`（执行者自评的批判性分析仅供参考，**不构成跨模型独立评审**，不冒充 PASS）；
> - 最终 per-stage evidence gate **无法运行，结论为 `BLOCKED`**（报告内如实呈现，不隐瞒）。
> 这不降低下面思路的价值，但请你在有 GPU 的服务器上做 pilot、并用你熟悉的 `/idea-evaluator` 或外部模型复核后再投入正式实验。

## Executive Summary

LRM 遗忘的核心矛盾是：敏感信息藏在 CoT 中间步骤而非仅答案，而"压制泄漏"与"保留通用推理能力"直接冲突。截至 2026-11，直接做"又一个 LRM 遗忘 loss"已是红海（R2MU、Reasoned IDK、FRUL/Selective Forgetting、CiPO、GUARD、STaR 已密集占位）。本轮发现的最高价值思路不是再造一个替代式遗忘方法，而是抓住三个尚未被巩固的缺口：(1) **解码策略一致性的因果机制与不变性目标**（ZeroThink/LessThink 暴露"假遗忘"，现有工作只把它当评测、没人做成训练目标或 certificates）；(2) **跨解码 × 跨算子（含压缩/量化）的审计协议**，与你已有的 D3/SpecGap 审计资产直接协同；(3) **"可验证的安全退出轨迹"作为可审计的遗忘目标**，把 NFRS 这类结构质量指标提升为带证书的约束。推荐首选 Idea 1（解码不变性 + 可证明一致性审计），并明确承接你既有的 SpecGap/D3 与 Table_TOFU_OU 资产。

## Literature Landscape

### 格局速览（截至 2026-11-23，含最新检索）

LRM 遗忘在 2025-2026 已形成完整链条，按"泄漏面 × 干预方式"可分四组：

| 工作 | 时间/venue | 核心 | 定位 |
|---|---|---|---|
| R-TOFU（Yoon et al.） | EMNLP 2025 | 首个 LRM 遗忘基准，step-wise 指标；Reasoned IDK；发现 ZeroThink/LessThink 解码陷阱 | 基准 + 基线 |
| R2MU（Zhang et al.） | EMNLP 2025 | 把 CoT + 答案表示映射到随机向量 | 表示破坏式基线（损害推理） |
| STaR | AAAI 2026 (arXiv 2601.09281) | 推理时免参数：敏感识别 + 安全前缀 + 轨迹抑制 + token 级过滤 | 推理时防御 |
| FRUL / Selective Forgetting | PAKDD 2026 (arXiv 2604.03571) | 多 LLM+RAG 定位敏感 CoT 片段、结构一致替换，配 reasoning-preservation loss | 替代式（需外部标注） |
| CiPO | ACL 2026 (arXiv 2604.15847) | 反事实轨迹 + 迭代 on-policy SimPO；因果 do-算子论证 | 当前最强替代式 SOTA |
| GUARD | 2026-09 | guided answer-reasoning distillation，学"自然遗忘轨迹"；提出 NFRS（结构/流畅/无替代支撑） | 轨迹质量导向 |
| R-MUSE | CVPR 2026 | 推理时激活转向：遗忘子空间 + 推理保留子空间(RRS)正交保护 + OT 自适应强度 | 推理能力保留导向 |
| Towards Reasoning-Preserving MLLM Unlearning | CVPR 2026 | RMLLMU-Bench（RIL/RCR）+ R-MUSE，扩展到多模态推理 | 多模态推理遗忘 |

### 结构性空白（多源交叉验证后仍成立）

1. **解码一致性只被当"评测陷阱"，未被做成训练目标或证书**。R-TOFU 发现 ZeroThink/LessThink 泄漏，STaR 做推理时过滤，但都没有一个"显式对多种解码策略的不变性进行约束/认证"的训练目标。此为最清晰的缺口。
2. **"推理能力 vs 推理内容"的解耦刚开始被占**（R-MUSE 的 RRS 是首个正交保护），但尚未与审计证书结合，也未见跨模型/跨规模的系统性验证。时间窗口紧（约 6-12 个月）。
3. **审计仍停留在"泄漏率"层面**。现有指标（AFE/CFE/leak@k/NFRS/RIL/RCR）度量的是"输出里有没有目标串"，没有回答"参数里是否还有"——这正是你 D3/SpecGap 的强项，可迁移到 LRM CoT。
4. **多解码 × 压缩算子（量化/剪枝）交叉无人做**。你既有的压缩链路不变性 insight 与 LRM 解码陷阱是两个空白的交集，几乎空白。
5. **RLVR（可验证奖励强化学习）推理的遗忘**尚系统（MAST 2026 是少数先驱），而 CiPO 的反事实迭代与 RLVR 的自生成轨迹天然契合。

### 红海避让（来自用户既有调研 + 本轮验证）

损失函数谱系（GA→NPO→SimNPO→SimPO/TPO）、权重定位/显著性、新 benchmark 空壳、蒸馏教师构造、单点攻击评估、单纯"替代式遗忘"（已被 CiPO 占满）——不要作为主贡献。

## Ranked Ideas

> 评分说明：Novelty / Feasibility / Evidence / Synergy(与你资产) 各 1-5；Pilot 一栏因无 GPU 统一标注 `needs manual pilot`，但给出"最小判别性实验"以便你在服务器上一锤定音。

### Idea 1 — ⭐ 首选：面向多解码一致性的 LRM 遗忘不变性目标 + 可审计证书
**假设**：现有方法在 DefaultThink 下"忘记"、在 ZeroThink/LessThink 下复活，根因是遗忘只作用于"带 CoT 的生成路径"，而直达答案的短路路径（shortcut path）未被约束。显式对解码策略做不变性正则，可同时关闭两类通道，且可给出"跨策略一致性证书"。
**做法**：把解码策略 $d\in\{$DefaultThink, LessThink, ZeroThink, SummaryThink$\}$ 视为一个"环境"，用类似 IRM（invariant risk minimization）的 penalty 约束遗忘损失在各策略下分布不变：$\min_\theta \sum_d \mathcal{L}_{\rm forget}^{(d)} + \lambda\|\nabla_w \mathcal{L}_{\rm forget}^{(d)}\cdot w\big|_{w=w_0}\|^2$；推理时输出一个"最大跨策略泄漏上界"作为审计证书（复用 SpecGap 的 TV/f-div 界技术）。
**评分**：Novelty 5 / Feasibility 4 / Evidence 4 / Synergy 5（直接接 D3/SpecGap）。
**最小判别性实验**：在 R-TOFU 上固定 forget01，对比 `R-TOFU 原方法` vs `+ 不变性 penalty` 在 DefaultThink/ZeroThink/LessThink 三策略下的 CFE 与 AFE 曲线；若基线在 ZeroThink 回升而本方法不回升，即验证假设。
**Novelty check**：最接近 STaR（推理时逐 token 过滤）与 R-TOFU（评测陷阱）；把一致性做成**训练目标 + 证书**是新的。✅ 无直接撞车，但需跟进 CiPO 后续。

### Idea 2 — 推理内容/能力解耦的"因果-子空间"遗忘（Causal-RRS）
**假设**：CiPO 的反事实（do-算子）与 R-MUSE 的 RRS 正交保护各自解决一半问题；二者结合可形式化"切断事实 F→CoT/答案的因果边，同时保持推理电路完整"，并给出比 R-MUSE 更强的可证明保留界。
**做法**：用因果图 $Q\to C\to A$（CiPO）定义遗忘干预，把遗忘更新投影到 RRS（推理保留子空间）的正交补（R-MUSE），并推导出保留界 $\|\Delta h_{\rm retain}\|\le\epsilon$ 的可认证形式。
**评分**：Novelty 4 / Feasibility 3 / Evidence 4 / Synergy 4。
**风险**：R-MUSE（CVPR 2026）刚占住正交保护，需明确差异化（因果 + 证书），否则像跟进工作。时间窗口紧。

### Idea 3 — LRM CoT 的"参数层审计"：把 SpecGap 提升到推理轨迹
**假设**：AFE/CFE/leak@k 只测输出串；LRM 的目标知识可能以"推理模式"而非"答案串"形式残留在参数中，可被 ZeroThink 或成员推断利用。用 D3/SpecGap 的 TV 界思路，构造对 CoT 隐状态分布的参数层证书。
**做法**：对 forget CoT 与 retain CoT 的隐状态分布做 f-divergence 盒约束，给出"目标轨迹不可被线性解码"的证书；与 FAT/ConceptVectors 类方法对比。
**评分**：Novelty 5 / Feasibility 4 / Evidence 5 / Synergy 5（与 D3/SpecGap 最强协同）。
**风险**：需要访问模型隐状态（白盒），闭源 LRM 不适用——正好与你的白盒审计定位一致。

### Idea 4 — 跨解码 × 压缩算子的遗忘不变性（LRM 版 DurableUn 扩展）
**假设**：LRM 在量化（INT4）后，被遗忘的 CoT 轨迹会比 LLM 更容易恢复，且不同解码策略下恢复幅度不同。需要统一"解码 × 压缩"的不变性理论与部署精度审计。
**做法**：把量化桶坍缩分析与多解码一致性结合，提出部署精度上的审计协议。
**评分**：Novelty 4 / Feasibility 3 / Evidence 4 / Synergy 5（压缩链路 + 审计双资产）。
**风险**：算力需求高（需量化多模型），适合作为 Idea 1 的扩展而非首发。

### Idea 5 — 可验证"安全退出轨迹"的 certificate（GUARD 的证书化）
**假设**：GUARD 的 NFRS 是经验质量分；可以把"安全退出"（不泄漏、结构完整、无幻觉替代）定义为可验证约束，用 RLVR 式奖励优化并给出满足概率下界。
**做法**：把安全退出建模为约束 MDP，用 Constrained Policy Optimization + concentration bound 给出"任意输入下违规概率 ≤ δ"的证书。
**评分**：Novelty 4 / Feasibility 3 / Evidence 3 / Synergy 4。

### Idea 6 — RLVR 推理的 on-policy 反事实遗忘
**假设**：CiPO 的迭代 on-policy 反事实天然适配 RLVR 自生成轨迹；把遗忘目标写成可验证奖励（禁止信息出现于任一推进步骤），用 GRPO 优化，比固定反事实更稳。
**做法**：GRPO + 反事实 chosen + 逐步 leak penalty。
**评分**：Novelty 4 / Feasibility 3 / Evidence 3 / Synergy 3。

### Idea 7 — 多解码一致性的基准与指标扩展（R-TOFU++）
**假设**：现有评测只报默认/单策略；构建系统性多解码 + 多算子 + 审计指标的统一基准，本身即贡献。
**评分**：Novelty 3 / Feasibility 5 / Evidence 5 / Synergy 4。适合作为任何方法论文的配套，而非单独主贡献。

### Idea 8 — 多模态推理遗忘（RMLLM）的重视角审计
**假设**：CVPR 2026 刚开 RMLLM 遗忘（R-MUSE/RMLLMU-Bench）；加入跨模态泄漏与推理能力双轴审计是增量。
**评分**：Novelty 3 / Feasibility 3 / Evidence 3 / Synergy 3（与你 L3 仓库协同）。

### Idea 9 — 顺序/持续 LRM 遗忘中的解码漂移
**假设**：连续遗忘请求会让"解码一致性"逐步退化；研究漂移度量与重校准。
**评分**：Novelty 4 / Feasibility 3 / Evidence 3 / Synergy 3。

### Idea 10 — 难度驱动的 LRM 遗忘调度（你 L2 方向的 LRM 版）
**假设**：CUD 的电路难度指标可迁移到 LRM CoT：易忘样本短路径、难样本长路径；据此分配算力/算法。
**评分**：Novelty 3 / Feasibility 4 / Evidence 3 / Synergy 5（接 L2 ForgetRoute）。

### 已淘汰方向（回避）
- 单纯新 loss（GA/NPO/SimPO 变体）——红海。
- 纯 benchmark 空壳——除非绑定 Idea 1 的证书。
- 纯推理时 prompt 过滤（STaR 类）——已被占。

## Novelty Verification

> 状态：`REVIEW_UNAVAILABLE`。本机无跨模型评审后端，以下是执行者基于多源检索的纸面核验（**非独立评审**）。

多源检索核验（arXiv / Semantic Scholar / ACL/CVPR Anthology / web）确认：
- Idea 1（多解码**不变性训练目标 + 证书**）：Core novelty 成立——最近邻 STaR（推理时过滤）与 R-TOFU（评测）均不做训练期不变性，也无证书。**但需持续监控 CiPO 后续工作**（其 future work 明确列出 adversarial prompt robustness，可能很快覆盖）。
- Idea 3（参数层 CoT 审计）：Core novelty 强——现有指标均为输出层，D3/SpecGap 尚未迁移到 CoT。
- Idea 2 / 4 / 5：与 R-MUSE / DurableUn / GUARD 有部分重叠，需靠"证书化 + 因果"做出差异，否则降为增量。

## External Critical Review

> 状态：`REVIEW_UNAVAILABLE`。无法调用真实跨模型评审；以下为**执行者自评的对抗性批判**（不得视为独立评审，请你在服务器上用外部模型复核）。

**对 Idea 1 的最强反对意见**：
1. "解码策略不变性"可能被审稿人质疑为人工设定（为什么要对 ZeroThink 不变？ZeroThink 本就不是标准推理路径）。**回应**：把它定位为"遗忘 robustness certificate"——用户对同一问题可能用任何推理预算交互，遗忘必须在整个预算谱上成立；这是 Privacy/Safety 需求，不是 benchmark hack。
2. 不变性 penalty（IRM 式）在 LLM 上 notoriously 不稳定。**回应**：先用简化的一阶一致性项（跨策略梯度对齐）做 pilot，IRM 作为 ablate 而非主方法。
3. 证书界可能太松而无实用价值。**回应**：先给"相对排序证书"（哪个方法在跨策略上更稳），再追求绝对界。

**最便宜的判别性实验**：见 Idea 1 的"最小判别性实验"——单卡 8B 模型 + R-TOFU forget01，2-3 小时可出初步曲线。

**评分（自评，仅供参考）**：Idea 1 = 8/10，Idea 3 = 8/10，Idea 2 = 7/10，Idea 4 = 7/10。

## Eliminated Ideas

| 想法 | 淘汰阶段 | 原因 |
|---|---|---|
| 新 LRM 遗忘 loss（SimPO/TPO 变体） | Phase 2 | 红海，CiPO/GUARD 已占替代式 |
| 纯 benchmark（R-TOFU++ 单独提交） | Phase 3 | 贡献太薄，除非绑定证书 |
| 纯推理时 prompt 过滤 | Phase 2 | STaR 已占 |

## 🏆 Recommendation

**首选 Idea 1：面向多解码一致性的 LRM 遗忘不变性目标 + 可审计证书。**
- 理由：缺口最清晰（训练目标 + 证书空白）、与用户 D3/SpecGap 审计资产最强协同、有最小判别性实验、且能自然扩展到 Idea 3（参数层审计）与 Idea 4（压缩交叉）。
- 备份 Idea 3：若你更想发挥白盒审计特长，可直接以"LRM CoT 参数层证书"为主。

## Refined Proposal / Next Steps

- 由于环境缺少评审门控 helper 与跨模型评审，本轮**不生成** `refine-logs/FINAL_PROPOSAL.md` 的"已验证"状态；仅给出 Idea 1 的可执行提案骨架（见下）。
- [ ] 在 GPU 服务器上跑 Idea 1 最小判别性实验（R-TOFU forget01，DeepSeek-R1-Distill-8B）。
- [ ] 用 `/idea-evaluator`（你的常用 skill）对 Idea 1/3 做五维评分复核。
- [ ] 若有正向信号 → `/research-refine-pipeline` 细化 → `/experiment-bridge` 实现 → `/auto-review-loop` 迭代。
- [ ] 把本轮新增近邻（CiPO/GUARD/R-MUSE）补入你的论文速览库与思维导图。

### Evidence Gate（如实呈现）

`BLOCKED`：缺 `run_state.py` / `idea_discovery_gate.py`，且两个 reviewer-bearing 阶段无实际跨模型 verdict。本报告不作为"通过完整流水线验证"交付。

---
*Source hashes / traces: 无（评审与门控工具不可用）。文献来源见正文链接；所有 novelty 结论为纸面核验，非跨模型裁决。*

## Appendix A — Idea 1 深化设计（/idea-creator）

完整叙事骨架（六幕故事 + 结构缺口 lens）与数学设计（核心量、不变性目标三层、审计证书三条路线、最小判别实验）见 `idea-stage/idea1_method_design.md`。要点：

- 故事定位：untested-assumption（遗忘只在默认路径被检验）+ diagnostic（泄漏作为推理预算的函数）+ contradiction（同一模型两种相反观测）+ method-transfer（IRM/DRO 迁移到解码维度）。
- 数学主线：定义解码条件泄漏率 $\rho_d$ 与遗忘鸿沟 $\Gamma=\max\rho_d-\min\rho_d$；命题 1 给出"$\Gamma\le\varepsilon$ 且 $\min\rho_d\le\delta$ ⇒ 所有策略 $\rho_d\le\delta+\varepsilon$"；主方法用一致性正则，IRM/DRO 为升级版；证书用 Hoeffding 界 / Lipschitz 连续预算 / SpecGap 的 TV 界缝合审计资产。
- 状态：DESIGN DRAFT，公式与命题待跨模型评审与 pilot 验证；命题 2（证书有效性）待严格证明。

## Appendix B — 推理期间遗忘：增量构思与排名（/idea-discovery）

围绕"推理时（training-free / inference-time）实现遗忘"，本轮新增 7 个构思并打分排名，详见 `idea-stage/inference_time_unlearning_ideas.md`（HTML 同名）。要点：

- 先给红海地图：Nullify（steering+null-space）、UCD（对比解码遗忘）、STaR、V-Steer、SafeSpec、SecureSD、SpecGuard 等已占据"推理时 steering/过滤/对比/KV 编辑/回滚"，单纯复刻不再新。
- 双口径排名：稳妥度第一 = LeakGuard（在线逐步泄漏探针 + 回滚 + SpecGap 证书，17/20，审计协同最强）；首创性第一 = Speculative Unlearning（把遗忘做成推测解码的接受准则 + TV 理论，新颖性 5/5）。
- 组合拳建议：LeakGuard（在线拦截）+ 思考预算调度（策略层）+ D3/SpecGap（证书层）可拼成完整的"推理时遗忘 + 审计"故事线。
