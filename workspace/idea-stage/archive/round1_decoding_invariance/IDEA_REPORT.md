# Idea Discovery Report

**Direction**: 解码不变性遗忘 + 可审计证书（由 `idea-stage/idea-1.md` 指定的深化草案）
**Date**: 2026-11-23
**Pipeline**: research-lit（网络检索）→ idea-creator（聚焦指定 idea）→ novelty-check → research-review（UNAVAILABLE）→ research-refine-pipeline（本地实例化）
**Assurance**: draft；`AUTO_PROCEED=true`
**Code/output root**: `/usr/local/workspace/R-TOFU/workspace/`

---

## Executive Summary

本轮以用户指定的 `idea-1.md` 为研究输入，未重新发散 8–12 个候选，而是把该草案收敛成一个**可在一张 H20 上 2 小时内证伪的最小判别实验**：先测已有 R2MU 已遗忘检查点在 4 种解码策略下的泄漏率 \(\rho_d\) 是否出现"假遗忘"鸿沟 \(\Gamma\)，再训练一个跨策略一致性 LoRA 模型看能否压平 \(\Gamma\)，最后检查 Hoeffding 证书在留出策略上的覆盖。

**当前证据状态**：文献定位与新颖性检索为 PROVISIONAL；跨模型评审 `REVIEW_UNAVAILABLE`；ARIS 证据门控 `BLOCKED`（缺 helper）。实验结论以 `refine-logs/EXPERIMENT_RESULTS.md` 中的实测数字为准，本报告不预先宣称任何结果成立。

---

## Literature Landscape

来源为 2026-11-23 的实时网络检索结果；仅列可点击的一手/二手来源，未核验条目明确标注。

| 主题 | 来源 | 与本 idea 的关系 |
|---|---|---|
| R-TOFU benchmark：CoT 轨迹泄漏、答案级遗忘不足、Reasoned IDK | [arXiv:2505.15214](https://arxiv.org/pdf/2505.15214v1.pdf)、[ACL Anthology 2025.emnlp-main.265](https://aclanthology.org/2025.emnlp-main.265/) | 直接基座。其评测沿默认生成路径，未把解码策略当自变量 |
| R2MU：推理模型遗忘、轨迹级遗忘 | [r2mu.netlify.app](https://r2mu.netlify.app/?trk=public_profile__posts-text)（项目页，待核验正式出处） | 本轮用作已遗忘基线检查点 |
| CiPO：反事实迭代偏好优化 | [alphaxiv 2604.15847](https://www.alphaxiv.org/tr/abs/2604.15847)、[EmergentMind 2604.15847](https://www.emergentmind.com/papers/2604.15847)（编号待核验） | 改进遗忘目标，未检验跨推理预算不变性 |
| GUARD：答案-推理解耦蒸馏、NFRS | [ACL Anthology 2026.emnlp-main.2334](https://aclanthology.org/2026.emnlp-main.2334.pdf) | 关注轨迹质量，未做策略谱不变性 |
| 不变性遗忘（对下游微调鲁棒） | [AMiner: ICML 2025, Invariance Makes LLM Unlearning Resilient…](https://www.aminer.cn/pub/683e5aa1163c01c850b0bd2e/invariance-makes-llm-unlearning-resilient-even-to-unanticipated-downstream-fine-tuning) | **最接近的不变性思想**，但不变性轴是下游微调，不是解码策略 |
| 推理时解码干预 SEGUE | [ACL Anthology 2026.acl-long.1850](https://aclanthology.org/2026.acl-long.1850) | 属"测/挡"，非训练约束 + 证书 |
| 统计保证：conformal / probabilistic 界 | [Google Research: Inference-time Unlearning Using Conformal Prediction](https://gweb-research2023-stg.uc.r.appspot.com/pubs/inference-time-unlearning-using-conformal-prediction)、[ICLR 2025 Oral: A Probabilistic Perspective on Unlearning and Alignment](https://www.cs.cit.tum.de/daml/probabilistic-unlearning/) | 证书思路可比，但对象是参数/数据影响而非解码策略谱 |
| NoThinking / 预填空思考块绕过 CoT | [百度百科「NoThinking方法」](https://baike.baidu.com/item/NoThinking%E6%96%B9%E6%B3%95/67731996)（百科，仅作现象定位，需回溯原始论文） | 支持"推理预算谱"是真实可控维度 |

**结构缺口（检索层面的判断，非定论）**：现有 LRM 遗忘工作集中在「忘什么 / 怎么忘 / 怎么测轨迹」，尚无检索到的 pub 明确把**解码策略（推理预算）当作一组环境**并同时给出不变性训练目标 + 泄漏上界证书。缺口类型：untested-assumption + diagnostic + method-transfer（沿用草案 lens）。

**局限**：本轮未下载全文 PDF、未跑 `/arxiv` 元数据核验、未做引文图谱；CiPO/GUARD/STaR/FRUL 的精确 arXiv 编号与发表状态未核验，故本报告不写入精确编号（除 R-TOFU 与 ACL Anthology 链接）。

---

## Ranked Ideas

本轮输入为指定草案，未做 idea-creator 的 8–12 路发散。以下为草案内部按**可实测性**排序的 3 个子命题（不是新 idea 池）：

| # | 子命题 | Pilot | 状态 |
|---|---|---|---|
| 1 | 诊断：已有遗忘检查点存在跨策略"假遗忘"鸿沟 \(\Gamma>0\)（C1） | M1 实测 | RECOMMENDED（先证伪） |
| 2 | 方法：跨策略一致性正则压平 \(\Gamma\) 且不毁效用（C2） | M2/M3 实测 | RECOMMENDED（依赖 #1） |
| 3 | 证书：Hoeffding + 鸿沟上界覆盖留出策略（C3） | M4 实测 | BACKUP（界松风险高） |

草案中 L2 IRM 梯度对齐、L3 DRO、路线 B Lipschitz、路线 C TV/SpecGap 缝合均**未进入本轮实现**：单卡预算与依赖不足，列为后续工作，不作为已验证贡献。

---

## Novelty Verification

- **检索式**（实际执行）：`R-TOFU unlearning large reasoning models think strategy zero-think leakage`；`LLM unlearning decoding strategy invariant risk minimization certified guarantee 2025 2026`；`"R2MU" OR "CiPO" OR "FRUL" OR "GUARD" OR "STaR" unlearning reasoning model`；`unlearning large reasoning model reasoning budget think prompt shortcut leakage zero thinking 2026`。
- **判定**：`PROCEED WITH CAUTION`（局部新颖性）。未检索到与「解码策略作为环境 + 一致性正则 + 有限策略集证书」三件套完全相同的工作；但 (a) 不变性遗忘 (ICML 2025) 与 (b) 推理预算/NoThinking 现象均已有先例，组合式新颖性弱于原草案叙事；(c) 检索为摘要级，存在近 3–6 个月并发工作未被发现的风险。
- **最接近工作**：R-TOFU（CoT 泄漏）、ICML 2025 不变性遗忘（不同不变性轴）、SEGUE（推理时解码干预）。
- **差异化点**：把 \(\rho_d\) 定义成**解码策略的函数**，把 \(\Gamma\) 变成训练目标与审计量，而非只做新指标。
- 未使用 `/novelty-check` 的跨模型交叉核验（评审后端不可用），因此该判定是执行者检索结论，标为 provisional。

---

## External Critical Review

> **REVIEW_UNAVAILABLE** — 本环境无 Codex MCP / `reviewer.json` / `reviewer_route.py`，`/research-review` 的跨模型评审槽位未执行；按工作流纪律，不得由执行者自评替代。

**执行者自审（明确标注：不是独立评审结论）**，已折进 `refine-logs/FINAL_PROPOSAL.md` §7：

1. `ZeroThink` 空 `<think>` 块是分布外前缀，"泄漏回升"可能来自 prompt 偏移而非知识残留 → 必须同时测 `target` 在同一前缀下的表现。
2. 一致性目标可能退化为"一律拒答" → 保留集 ROUGE-L 是硬护栏。
3. 实体抽取器（gold answer 中最长大写短语）可能误抽 → 并报 ROUGE-L 与逐样本输出文本。
4. `forget01` 的 `task_id==1` 仅 40 题，统计功效低 → 结论限定为 pilot。
5. Hoeffding 界在 n≈40 时很松，"覆盖率高"不等于保证有用 → 必须同时报告界宽。
6. 命题 2（证书严格有效性）仍为开放项：\(\widehat\Gamma\) 是估计量，草案中未给出其置信处理，不能直接当作定理使用。

---

## Eliminated Ideas

- **草案 L2/L3（IRM / DRO）作为主方法**：暂缓。理由：LLM 上 IRM penalty 不稳定、单卡预算不足；且主方法需要可快速证伪的简单基线（L1）。
- **路线 B（连续预算 Lipschitz 证书）**：降为 M4 的经验观察，不做 K 的严格界定。
- **路线 C（TV/SpecGap 缝合）**：未实现，缺既有 D3/SpecGap 可执行代码资产。
- **GPT-as-judge 泄漏判分**：未实现，`test_cot.py` 需外部 API key，本环境不可用；改用数据集 gold answer 的实体匹配 + ROUGE-L，避免引入模型输出作为 ground truth。

---

## Refined Proposal

- Proposal: `refine-logs/FINAL_PROPOSAL.md`
- Experiment plan: `refine-logs/EXPERIMENT_PLAN.md`
- Tracker: `refine-logs/EXPERIMENT_TRACKER.md`
- Research contract: `idea-stage/docs/research_contract.md`
- Results (实测后): `refine-logs/EXPERIMENT_RESULTS.md`、`results/ANALYSIS.md`
- Code: `code/`（全部位于 `workspace/`）

---

## Per-Stage Evidence Gate

> **BLOCKED** — 按 `idea-discovery` 的 `RESUMABLE=true` 契约，需要 `run_state.py` / `idea_discovery_gate.py` 与 cross-family 评审回执。本环境：
> - 找不到 `run_state.py`、`idea_discovery_gate.py`、`reviewer_route.py`（标准解析链 `.aris/tools/` → `tools/` → `$ARIS_REPO/tools/` → `~/.aris/repo/tools/` 全为空）；
> - 找不到 `shared-references/` 与 `templates/RESEARCH_CONTRACT_TEMPLATE.md`；
> - 无跨模型评审后端，无法产生 `accept` 回执。
>
> 因此本报告的 `gates.idea-discovery-evidence` 判定为 **BLOCKED**，不得视为通过完整 W1 门控。已完成的实质工作（文献定位、契约、方案、计划、实现）照常保留并明确标注证据等级。

---

## Next Steps

- [x] M0 sanity → M1 基线诊断 → M2 训练 → M3 主结果 → M4 预算网格（见 tracker 实际状态）
- [ ] 补齐跨模型评审后端后重跑 `/research-review` 与证据门控
- [ ] 若 S1/S2 通过：按 `/ablation-planner` 扩展 λ 消融与多 seed
- [ ] 若 S1 被否证：以 informative negative 记录，不改写核心假设
- [ ] 后续再考虑 `/auto-review-loop` 与论文写作（本轮 `assurance: draft`）


## 补充更正（2026-11-23，执行者 B）

「Eliminated Ideas」中「GPT-as-judge 泄漏判分未实现、本环境不可用」**已过时**：
用户随后提供了 Hy4 OpenAI 兼容端点，已接入 `code/llm_judge.py` 作为第二套泄漏指标。
更正后的定位：LLM 判分是**指标**而非独立评审；hy4 与执行者同家族，`REVIEW_UNAVAILABLE`
与 `gates.idea-discovery-evidence = BLOCKED` 结论不变。
