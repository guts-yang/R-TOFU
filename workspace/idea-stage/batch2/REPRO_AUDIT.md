# 第二批 Idea 复现审计（Round 1）

**日期**: 2026-11-23
**对象**: `idea-stage/idea-2.md`（Idea Discovery Report — 大推理模型机器遗忘创新）
**方法**: 实时网络检索逐条核验 + 本机环境实测 + 文件存在性检查
**判定口径**: VERIFIED（有一手/权威二手来源）/ PARTIAL（编号或会议对，作者或细节有误）/ UNVERIFIED（检索不到）/ CONTRADICTED（与实测不符）

## A. 环境声明复现 —— 与本机实测不符（重要）

| `idea-2.md` 声明 | 本机实测（2026-11-23） | 判定 |
|---|---|---|
| `torch 2.8.0`、`cuda=False`，无 GPU，pilot 只能 `needs manual pilot` | `nvidia-smi`：1×NVIDIA H20 96GB；`/usr/local/bin/python`：torch 2.5.1+cu124，`cuda=True`；4 个 venv：torch 2.5.1+cu121，`cuda=True` | **CONTRADICTED** |
| 跨模型评审 MCP 不可用 | 无 Codex MCP / `reviewer.json` / `reviewer_route.py` | VERIFIED（仍成立） |
| `run_state.py` / `idea_discovery_gate.py` 缺失 | 标准解析链全为空；`shared-references/`、`templates/` 亦缺失 | VERIFIED（仍成立） |

**后果**：`idea-2.md` 的「全部 pilot 标注 needs manual pilot」是错误前提下的降级。本轮已实际部署 GPU pilot（M0–M4），因此该报告的核心待验证命题（Idea 1 的判别性实验）不再只是纸面建议。
**运行时修正**：最初使用的 `torch 2.5.1+cu121` + `transformers 4.43.0` 在 H20 上启用 KV-cache 的 decode step 触发原生 `SIGFPE`（faulthandler 定位到 `torch/nn/modules/linear.py:125` → `LlamaMLP`）；切到 `torch 2.5.1+cu124` + `transformers 4.48.2` 并补齐 `rouge-score/peft/accelerate` 后缓存生成正常。这是环境/驱动层问题，不是训练脚本缺陷，按 `/experiment-bridge` 的 stop condition 归类为环境修复。

## B. 引用逐条核验

| `idea-2.md` 条目 | 核验来源 | 判定 |
|---|---|---|
| R-TOFU, Yoon et al., EMNLP 2025；ZeroThink/LessThink 解码陷阱 | [ACL Anthology 2025.emnlp-main.265](https://aclanthology.org/2025.emnlp-main.265/)（摘要明确写出该 failure mode）；[arXiv 2505.15214](https://arxiv.org/pdf/2505.15214v1.pdf)；作者 Sangyeon Yoon, Wonje Jeung, Albert No | **VERIFIED** |
| R2MU, Zhang et al., EMNLP 2025 | 实为 *Reasoning Model Unlearning: Forgetting Traces, Not Just Answers…*，[ACL Anthology 2025.emnlp-main.220](https://aclanthology.cn/2025.emnlp-main.220)，第一作者 **Changsheng Wang**（Yihua Zhang 为共同作者） | **PARTIAL**（作者标注不精确） |
| STaR, AAAI 2026, arXiv 2601.09281 | [arXiv 2601.09281](https://arxiv.org/html/2601.09281v1)、[AAAI v40i41 pp.35121-35129](https://acm-prod.literatumonline.com/doi/10.1609/aaai.v40i41.40818)，作者 Jingjing Zhou, Gaoxiang Cong, Li Su, Liang Li | **VERIFIED** |
| FRUL / Selective Forgetting, PAKDD 2026, arXiv 2604.03571 | [arXiv 2604.03571](https://searcharxiv.com/abs/2604.03571)、[PAKDD 2026 LNCS pp.412-423](https://acm-prod.literatumonline.com/doi/10.1007/978-981-92-1468-6_28) | **VERIFIED**（但作者元数据在不同聚合站冲突：Tuan Le/Wei Qian/Mengdi Huai vs 其它来源，故不引用作者名） |
| CiPO, ACL 2026, arXiv 2604.15847 | [ACL Anthology 2026.acl-long.143](https://aclanthology.org/2026.acl-long.143/)、[arXiv 2604.15847](https://scirate.com/arxiv/2604.15847)，作者 Junyi Li, Yongqiang Chen, Ningning Ding | **VERIFIED** |
| GUARD（2026-09, NFRS） | [ACL Anthology 2026.emnlp-main.2334](https://aclanthology.org/2026.emnlp-main.2334.pdf)（EMNLP 2026），NFRS 指标属实 | **PARTIAL**（应标 venue 而非月份） |
| R-MUSE / RMLLMU-Bench, CVPR 2026 | [CVF Open Access CVPR 2026 pp.10251-10261](https://openaccess.thecvf.com/content/CVPR2026/html/Li_Towards_Reasoning-Preserving_Unlearning_in_Multimodal_Large_Language_Models_CVPR_2026_paper.html)、[CVPR 虚拟海报](https://cvpr.thecvf.com/virtual/2026/poster/38833) | **VERIFIED**（注意是**多模态**推理遗忘，不是纯文本 LRM） |
| MAST 2026（RLVR 遗忘先驱） | 多轮检索未命中 | **UNVERIFIED** |
| Appendix B: Nullify | [arXiv 2610.10655](https://alphaxiv.org/abs/2610.10655v1) | VERIFIED |
| Appendix B: UCD | [arXiv 2506.12097](https://ar5iv.arxiv.org/html/2506.12097) | VERIFIED |
| Appendix B: SecureSD | arXiv 2610.08678（IEEE S&P 2027 收录说法来自二手站） | PARTIAL |
| Appendix B: SpecGuard | [arXiv 2604.15244](https://arxiv.org/abs/2604.15244) / [arXiv 2609.11799](https://arxiv.org/html/2609.11799v1) 真实存在，但主题是**推测解码验证 / 后门检测**，与「遗忘」无关 | **CONTRADICTED**（上下文误置） |
| Appendix B: V-Steer / SafeSpec / LeakGuard / Speculative Unlearning | 多轮检索未命中 | **UNVERIFIED**（很可能是本轮构思名，不应写成「已占位的已有工作」） |

## C. 关键新颖性修正（本轮最重要的复现发现）

`idea-2.md` 断言：「解码一致性只被当『评测陷阱』，未被做成训练目标或证书」。检索显示 **STaR (AAAI 2026) 已正式提出 Multi-Decoding Consistency Score (MCS)**，其定义是「对整个解码策略空间的最坏情况泄漏量化」（[arXiv HTML](https://arxiv.org/html/2601.09281v1)），并配多粒度 MIA 指标。这与草案的 $\Gamma=\max_d\rho_d-\min_d\rho_d$ / $\max_d\rho_d$ 在概念上高度接近。

- 因此 **"多解码一致性"作为评测量已被占位**，Idea 1 的 Novelty=5/5 应下调；贡献必须严格收窄为：**(i) 把一致性写成训练目标（跨策略不变性正则），(ii) 给出带置信度的泄漏上界证书**。二者在检索到的 STaR / R-TOFU / CiPO / GUARD 中均未见。
- 论文写作时必须正面引用并对比 MCS，否则极易被审稿人判定为「已有指标换名」。

## D. 断链引用（可复现性缺陷）

`idea-2.md` Appendix A 指向 `idea-stage/idea1_method_design.md`、Appendix B 指向 `idea-stage/inference_time_unlearning_ideas.md`（及同名 HTML）——**三个文件在本仓库均不存在**。

- Appendix A 的实质内容大概率对应现存的 `idea-stage/idea-1.md`（六幕叙事、结构缺口 lens、$\rho_d$/$\Gamma$、L1/L2/L3、证书三路线、最小判别实验均一致），本轮已按该文件补全并落到 `refine-logs/FINAL_PROPOSAL.md`。
- Appendix B 的 7 个推理时构思无源文件，仅能从 `idea-2.md` 正文的要点复现，无法复现完整打分表；本轮将其标为「不可复现，需原始资产」。

## E. 复现结论

1. 方向判断（红海避让、Idea 1 优先、与 D3/SpecGap 协同）**大体成立**；
2. 但「无 GPU」前提错误、STaR MCS 遗漏、两处附件断链、Appendix B 若干工作名/主题未经核验 —— 该报告不能直接作为论文 related work 使用；
3. 本轮已用实测 pilot 补齐 Idea 1 的判别性证据，并在 Round 2 用证据反推排名（见 `IDEA_REPORT_round2.md`）。


## 6. 后续补充（2026-11-23，执行者 B）

- 用户补充了 `/usr/local/workspace/.env` 的 Hy4 LLM 评测配置；已接入 `code/llm_judge.py`，
  详见 `LLM_JUDGE_INTEGRATION.md`。这只补齐**指标评测**，不补齐跨模型评审或门控 helper，
  故 §1 的 `REVIEW_UNAVAILABLE` / `BLOCKED` 仍然成立。
- GPU 侧另发现 `torch 2.5.1+cu121` 在 H20 上 KV-cache 解码步的 bf16/fp16 linear 会 SIGFPE；
  `fp32` 或 `2.5.1+cu124` 可规避。该问题与「有无 GPU」是两件事，原报告的「无 GPU」判断仍属错误。
