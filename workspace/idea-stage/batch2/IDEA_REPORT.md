# Idea Discovery Report — 第二批（Round 1，全量复现）

**Direction**: 对 LRM 机器遗忘进行创新（输入 `idea-stage/idea-2.md`）
**Date**: 2026-11-23
**Pipeline**: `/research-pipeline` Stage 1→4（`AUTO_PROCEED=true`, `AUTO_WRITE=false`）
实际链路：`research-lit`（检索）→ `idea-creator`（重排）→ `novelty-check` → `research-review`（UNAVAILABLE）→ `research-refine-pipeline`（契约/计划）→ `experiment-bridge`（GPU pilot）→ `auto-review-loop`（BLOCKED）→ `summary`
**代码/输出根**: `/usr/local/workspace/R-TOFU/workspace/`

---

## Executive Summary

对第二批 10 个 idea 做了全量复现：先核验环境与引用，再重排、再做实测 pilot。三项复现发现改变了原报告结论：

1. **环境前提被推翻**：`idea-2.md` 称「无 GPU、pilot 只能手工」，本机实测为 1×H20 96GB + CUDA torch。本轮已实际跑完 M0 sanity 并部署 M1–M4 GPU pilot（结果见 `refine-logs/EXPERIMENT_RESULTS.md`）。
2. **最关键的近邻被漏掉**：STaR (AAAI 2026) 已提出 **Multi-Decoding Consistency Score (MCS)**——量化整个解码策略空间的最坏情况泄漏。因此「多解码一致性」作为**评测指标已被占位**，Idea 1 的新颖性必须从「提出一致性」收窄为「把一致性做成**训练目标** + **带置信度的证书**」。
3. **两处附件断链**：Appendix A/B 指向的 `idea1_method_design.md`、`inference_time_unlearning_ideas.md` 在仓库中不存在；Appendix B 的 7 个推理时构思无法完整复现。

详见 `idea-stage/batch2/REPRO_AUDIT.md`。

---

## Literature Landscape（已核验）

| 工作 | 一手/权威来源 | 与本方向关系 |
|---|---|---|
| R-TOFU (EMNLP 2025) | [ACL 2025.emnlp-main.265](https://aclanthology.org/2025.emnlp-main.265/), [arXiv 2505.15214](https://arxiv.org/pdf/2505.15214v1.pdf) | 基准；明确记录 ZeroThink/LessThink 泄漏复活的 failure mode |
| R2MU (EMNLP 2025) | [ACL 2025.emnlp-main.220](https://aclanthology.cn/2025.emnlp-main.220) | 表示破坏式遗忘基线（本轮 checkpoint 来源） |
| STaR (AAAI 2026) | [arXiv 2601.09281](https://arxiv.org/html/2601.09281v1), [AAAI v40i41](https://acm-prod.literatumonline.com/doi/10.1609/aaai.v40i41.40818) | 推理时轨迹抑制；**已提出 MCS 多解码一致性指标** ← 最强近邻 |
| FRUL / Selective Forgetting (PAKDD 2026) | [arXiv 2604.03571](https://searcharxiv.com/abs/2604.03571) | 敏感 CoT 片段替换 + reasoning-preservation loss |
| CiPO (ACL 2026) | [ACL 2026.acl-long.143](https://aclanthology.org/2026.acl-long.143/), arXiv 2604.15847 | 反事实轨迹 + 迭代 on-policy SimPO，替代式 SOTA |
| GUARD (EMNLP 2026) | [ACL 2026.emnlp-main.2334](https://aclanthology.org/2026.emnlp-main.2334.pdf) | 安全退出轨迹 + NFRS 结构质量指标 |
| R-MUSE / RMLLMU-Bench (CVPR 2026) | [CVF Open Access](https://openaccess.thecvf.com/content/CVPR2026/html/Li_Towards_Reasoning-Preserving_Unlearning_in_Multimodal_Large_Language_Models_CVPR_2026_paper.html) | 多模态推理遗忘；推理保留子空间正交保护 |
| ICML 2025 不变性遗忘 | [AMiner](https://www.aminer.cn/pub/683e5aa1163c01c850b0bd2e/invariance-makes-llm-unlearning-resilient-even-to-unanticipated-downstream-fine-tuning) | 不变性轴是下游微调，非解码策略 |
| SEGUE (ACL 2026) | [ACL 2026.acl-long.1850](https://aclanthology.org/2026.acl-long.1850) | 推理时熵引导解码干预 |
| conformal / probabilistic 界 | [Google Research](https://gweb-research2023-stg.uc.r.appspot.com/pubs/inference-time-unlearning-using-conformal-prediction), [ICLR 2025 Oral](https://www.cs.cit.tum.de/daml/probabilistic-unlearning/) | 统计保证思路可比，对象不是解码策略谱 |
| Nullify / UCD / SecureSD | [2610.10655](https://alphaxiv.org/abs/2610.10655v1), [2506.12097](https://ar5iv.arxiv.org/html/2506.12097), 2610.08678 | Appendix B 中确实存在的推理时/推测解码工作 |

**结构性缺口（修正后）**：解码策略一致性作为**评测**已有 MCS；作为**训练约束**与**高置信证书**仍未见公开工作。缺口类型从 `untested-assumption` 降级为 `method-transfer + certificate gap`，窗口更窄。

---

## Ranked Ideas（复现后重排）

| # | Idea | 原评分 | 复现后 | 变化理由 |
|---|---|---|---|---|
| 1 | 多解码不变性训练目标 + 可审计证书 | N5/F4/E4/S5 | **N3/F4/E5/S5** | STaR MCS 占位「一致性评测」，新颖性下调；但本轮**已有 GPU pilot 资产**，Evidence 上调 |
| 2 | Idea 3：LRM CoT 参数层审计（SpecGap 迁移） | N5/F4/E5/S5 | **N4/F4/E4/S5** | 仍未被占位；白盒 8B 可做，但本轮未实现 |
| 3 | Idea 4：跨解码 × 压缩算子不变性 | N4/F3/E4/S5 | N4/F2/E4/S5 | 需量化多模型，算力门槛高 |
| 4 | Idea 2：因果-子空间 Causal-RRS | N4/F3/E4/S4 | N3/F3/E4/S4 | R-MUSE 已占正交保护，且为多模态设定 |
| 5 | Idea 5：安全退出轨迹证书 | N4/F3/E3/S4 | N3/F3/E3/S4 | GUARD/NFRS 已占轨迹质量 |
| 6 | Idea 9：持续遗忘中的解码漂移 | N4/F3/E3/S3 | N3/F3/E3/S3 | 需 MCS 作为基础指标，差异化变薄 |
| 7 | Idea 6：RLVR on-policy 反事实遗忘 | N4/F3/E3/S3 | N3/F2/E3/S3 | 与 CiPO 迭代近邻，算力高 |
| 8 | Idea 7：R-TOFU++ 基准扩展 | N3/F5/E5/S4 | N2/F5/E5/S4 | MCS 已提供多解码指标，纯基准贡献更薄 |
| 9 | Idea 8：多模态推理遗忘审计 | N3/F3/E3/S3 | N3/F2/E3/S3 | R-MUSE 已开 |
| 10 | Idea 10：难度驱动遗忘调度 | N3/F4/E3/S5 | N3/F3/E3/S5 | LRM CoT 难度指标尚无公开定义 |
| — | Appendix B：7 个推理时构思 | 17/20 等 | **不可复现** | 源文件缺失；LeakGuard / Speculative Unlearning / V-Steer / SafeSpec 名称未核验 |

**AUTO_PROCEED 选择**：Idea 1（与第一批 `idea-1.md` 同一核心命题），继续 Stage 2 实验桥接。

---

## Novelty Verification

- 检索式（实际执行）：STaR/FRUL/CiPO/GUARD/R-MUSE/R2MU/R-TOFU 的编号与 venue 组合查询、`Multi-Decoding Consistency Score` 专项查询、推理时遗忘方法名查询。
- **判定**：`PROCEED WITH CAUTION`。核心贡献必须写成「训练期不变性约束 + Hoeffding 证书」，并显式与 STaR 的 MCS 对比；若只写「多解码一致性」则与已有工作撞车。
- 未使用跨模型 novelty 复核（后端不可用），为执行者检索结论。

---

## External Critical Review

> **REVIEW_UNAVAILABLE**：无跨模型评审后端，`/research-review` 与 `/auto-review-loop` 均未执行；不得由执行者自评替代。

执行者自审（非独立评审）：
1. MCS 已定义最坏情况泄漏 → 必须把「为什么训练约束比评测指标更强」讲清楚，否则贡献被判增量。
2. Hoeffding + 估计鸿沟在小样本下界极松 → 只能作相对排序证书，不能宣称「已证明安全」。
3. 跨策略前缀为分布外 prompt → 泄漏回升可能混有 prompt 偏移，需 target 模型同前缀对照（实验已包含）。
4. 全拒答退化风险 → 保留集 ROUGE-L 是硬护栏（S3）。
5. `forget01/task_id=1` 仅 40 题 → 结论限定为 pilot。

---

## Eliminated Ideas

- 纯「多解码一致性指标」作为主贡献：已由 STaR MCS 占位。
- Appendix B 的 LeakGuard / Speculative Unlearning 作为「已有工作」引用：名称未核验，不得写入 related work。
- SpecGuard：真实工作但主题是推测解码验证/后门检测，与遗忘无关，从红海地图移除。
- MAST 2026：未核验，不作为 RLVR 遗忘先驱引用。
- 全参训练 / GSM8K-MMLU 外部 benchmark / 多 seed：本轮预算外，列为后续。

---

## Refined Proposal / 工件

- 契约：`idea-stage/docs/research_contract.md`
- 方案：`refine-logs/FINAL_PROPOSAL.md`
- 计划 / Tracker：`refine-logs/EXPERIMENT_PLAN.md`、`EXPERIMENT_TRACKER.md`
- 代码：`code/`；结果：`results/`、`refine-logs/EXPERIMENT_RESULTS.md`
- 复现审计：`idea-stage/batch2/REPRO_AUDIT.md`

---

## Per-Stage Evidence Gate

> **BLOCKED**：`run_state.py` / `idea_discovery_gate.py` / `reviewer_route.py` / `shared-references/` / `templates/` 均不可用，且无跨模型 verdict 可记录 `accept`。`/research-pipeline` 的 Stage 1 与 Stage 3 因此不能标 `accepted`；Stage 2 由实际 job 完成情况判定，Stage 4 由文件存在性判定。全程不伪造门控回执。

---

## Next Steps

- [ ] M1–M4 GPU pilot 完成 → 汇总实测数字
- [ ] 用实测证据做 **Round 2 `/idea-discovery` 复现**（见 `IDEA_REPORT_round2.md`）
- [ ] 补齐评审后端后重跑 Stage 1/3 门控
- [ ] 若 S1/S2 通过 → `/ablation-planner` 扩展 λ 消融与多 seed


## Round 1 补充（2026-11-23，执行者 B）

用户补充 Hy4 LLM 评测配置后，`/experiment-bridge` 阶段新增 M5a（实体指标重算）与
M5b（Hy4 LLM-as-judge）。**结论**：新增的是第二套评测指标，不是跨模型独立评审；
`REVIEW_UNAVAILABLE` 与 `BLOCKED` 不变。详见 `batch2/LLM_JUDGE_INTEGRATION.md`
与 `refine-logs/EXPERIMENT_RESULTS.md` 的 LLM-as-judge 小节。
