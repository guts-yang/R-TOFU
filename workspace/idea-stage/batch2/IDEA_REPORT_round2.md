# Idea Discovery Report — 第二批 · Round 2（再次 `/idea-discovery` 复现）

**触发**: 用户要求「复现完之后就使用 `/idea-discovery` 再次进行复现」
**日期**: 2026-11-23
**输入**: `idea-2.md` + `batch2/IDEA_REPORT.md`（Round 1）+ `batch2/REPRO_AUDIT.md` + **实测证据** `refine-logs/EXPERIMENT_RESULTS.md` / `NARRATIVE_REPORT.md`
**Mode**: `AUTO_PROCEED=true`；同一工作流、全新证据条件；不复制 Round 1 结论

---

## Phase 0 — Research Brief

合并三份输入。新增硬约束来自实测：

- target 基座当前**不能稳定复现虚构事实**（`DefaultCoT` 实体泄漏 0.025、`truncated_rate` 0.975、抽检为退化文本）。
- 拒绝式 LoRA SFT 使方法组与对照组同时退化为「一律拒答」（retain ROUGE-L 0.014 / 0.018 vs target 0.180）。
- 因此任何以 \(\rho_d\) / \(\Gamma\) 为因变量的结论，在本轮测量链上**不可解释**。

## Phase 1 — Literature Survey（二次核验）

Round 1 结论保持不变，并新增一条决定性近邻：**STaR (AAAI 2026, arXiv 2601.09281)
已提出 Multi-Decoding Consistency Score (MCS)** —— 量化整个解码策略空间的最坏情况泄漏。
即「多解码一致性」作为**评测指标**已被占位。来源见 `batch2/REPRO_AUDIT.md` §2。
其余近邻：R-TOFU / R2MU (EMNLP 2025)、CiPO、GUARD/NFRS、FRUL (PAKDD 2026)、
R-MUSE (CVPR 2026)、ICML 2025 不变性遗忘、SEGUE。

## Phase 2 — Idea Generation / Ranking（结构性 pivot）

**与 Round 1 的关键分歧**：Round 1 在纸面上把 Idea 1 排第一（N5）；Round 2 拿到实测后认为
**首要缺口不是「缺一个不变性训练目标」，而是「缺一个可信的多解码测量协议」**。
这是结构性转向（研究对象从训练目标 → 测量有效性），不是调参。

| # | Idea | R1 | R2 | 变化理由 |
|---|---|---|---|---|
| 1 | **可复现的多解码泄漏测量协议**（基座校验 + 截断护栏 + 官方指标 + MCS 对照） | 隐含于 Idea 7 | **1 / RECOMMENDED** | 本轮失败的直接根因；不做这一步其余 \(\rho_d\) 实验不可解释 |
| 2 | Idea 3：LRM CoT 参数层审计（SpecGap/D3 迁移） | 2 | 2 | 白盒隐状态不依赖退化生成文本，抗当前失效模式 |
| 3 | Idea 1：不变性训练目标 + 证书 | 1 | **3 / BACKUP** | MCS 占位 + 本轮负向 pilot；须待 #1 完成后才有意义 |
| 4 | Idea 7：R-TOFU++ 多解码/多算子基准 | 8 | 4 | 与 #1 合并后才有价值 |
| 5 | Idea 4：跨解码 × 压缩算子 | 3 | 5 | 算力门槛高 |
| 6 | Idea 2：Causal-RRS | 4 | 6 | R-MUSE 已占正交保护 |
| 7 | Idea 5：安全退出轨迹证书 | 5 | 7 | GUARD/NFRS 已占轨迹质量 |
| 8 | Idea 9：持续遗忘解码漂移 | 6 | 8 | 依赖 MCS 作为基础指标 |
| 9 | Idea 6：RLVR on-policy 反事实 | 7 | 9 | 与 CiPO 近邻、算力高 |
| 10 | Idea 8：多模态推理遗忘 | 9 | 10 | 需新基座 |
| 11 | Idea 10：难度驱动调度 | 10 | 11 | 难度指标未定义 |
| — | Appendix B 7 个推理时构思 | 不可复现 | 不可复现 | 源文件缺失；自造名与已发表工作混列 |

**AUTO_PROCEED 选择**：#1 测量协议优先；Idea 1 保留 BACKUP，待测量链修好后重启。

## Phase 3 — Novelty Verification

- 检索层面仍为 `PROCEED WITH CAUTION`。
- #1 的新颖性**不在**「提出一致性指标」（MCS 已占），而在「把**测量有效性**本身写成 LRM 遗忘的前置条件：
  基座复现率下限、截断率护栏、跨策略同题配对、与 MCS/证书的一致性对照」。
  未检索到直接撞车工作，但协议类贡献新颖性偏弱，宜作为方法论文配套而非独立主贡献。
- Idea 3 仍是最强的一手空白，但需全文级查新（本轮只做摘要级）。

## Phase 4 — External Critical Review

`REVIEW_UNAVAILABLE`（原因同 `review-stage/AUTO_REVIEW.md`）。
执行者自审（**不是独立评审**）：#1 可能被质疑为「工程修正而非研究贡献」——
回应方式是把「基座复现率 / 截断率 / 跨策略方差」写成可证伪的前置判据并公开负向结果，
而不是只修代码。

## Phase 4.5 — Refined Proposal（最小判别实验，结构性 pivot）

1. **Gate-0（新增硬门槛）**：用 R-TOFU 官方 `eval.py`/`eval2.py` 或等价生成协议，
   测 `LRM-target` 在 forget01 上的 exact-match / ROUGE 复现率。若 < 0.5，
   先修 prompt 模板、解码参数或更换目标检查点；**未通过 Gate-0 前不得跑任何 \(\Gamma\) 实验**。
2. **Gate-1**：把 `truncated_rate` 纳入护栏，要求 < 0.2；否则增大 `max_new_tokens`
   或改用带 `</think>` 停止准则的解码。
3. **Gate-2**：训练目标从「全量拒绝 SFT」换成 R-TOFU 的 GA/GD（或 NPO）+ 保留集 KL，
   确保 retain ROUGE-L 下降 ≤0.10，再比较不变性项与单策略对照。
4. **Gate-3**：加入 STaR 的 MCS 作为对照指标，把「训练约束 + 证书」与 MCS 显式分开陈述。
5. 证书在小 n 下界过松，改用相对排序证书或扩大样本后再谈绝对界。

## Phase 5 — 复现一致性检查

| 维度 | Round 1 | Round 2 | 是否一致 |
|---|---|---|---|
| 环境前提（有无 GPU） | 已修正为有 GPU | 一致 | ✅ |
| 引用核验（MCS 遗漏等） | 已记录 | 一致 | ✅ |
| Idea 1 首选 | 是 | **否（降为 #3）** | ❌ 因新增实测负证据合理翻转 |
| Evidence Gate | BLOCKED | BLOCKED | ✅ |
| Reviewer | UNAVAILABLE | UNAVAILABLE | ✅ |

结论：两次复现在**文献与环境事实**上一致；在**排名**上因新证据发生一次结构性翻转，
已记录理由，不是随机分歧。

## Evidence Gate

`BLOCKED` — 仍缺 `run_state.py` / `idea_discovery_gate.py` 与跨家族评审回执。
Hy4 端点仅作指标判分（同家族，不可作 reviewer）。本 Round 2 报告不作为「通过完整 W1 门控」交付。

## Next Steps

- [ ] 执行 Gate-0/1/2/3，重跑最小判别实验
- [ ] 补齐跨模型评审后端与门控 helper 后重跑 `/idea-discovery` 与 `/auto-review-loop`
- [ ] 若 Gate-0 通过且 Γ 显著，再回到 Idea 1 的不变性训练目标
