# FINAL PROPOSAL — 解码不变性遗忘（DIU）

**日期**: 2026-11-23
**输入**: `workspace/idea-stage/idea-1.md`
**状态**: 方法已冻结（Problem Anchor 见 `idea-stage/docs/research_contract.md`），实验待实测

## 1. Problem Anchor

遗忘是**对解码策略普适**的性质，而不是默认 CoT 路径下的属性。现有 LRM 遗忘只在默认路径评测，留下"换个问法知识复活"的结构缺口。

## 2. Method Thesis（一句话）

把解码策略（推理预算）当作多个训练环境，用「跨策略一致的安全响应监督 + 保留侧约束」替代单路径遗忘目标，并用有限策略集上的集中不等式给出泄漏上界证书。

## 3. 形式化（沿用草案符号，收窄到可实测版本）

- 策略集 \(\mathcal D=\{\text{DefaultCoT},\text{LessThink},\text{ZeroThink},\text{SummaryThink}\}\)。
- 策略 \(d\) 下的解码条件泄漏率 \(\rho_d(\theta)=\mathbb E_{x\sim D_f}[\ell(\hat a,z;s)]\)，其中 \(\ell=1\) 当且仅当 gold answer 中的目标专有实体出现在生成轨迹或答案中（另报连续代理 ROUGE-L recall）。
- 遗忘鸿沟 \(\Gamma(\theta)=\max_d\rho_d-\min_d\rho_d\)。
- **命题 1**（草案中已自洽）：\(\Gamma\le\varepsilon \wedge \min_d\rho_d\le\delta \Rightarrow \forall d,\rho_d\le\delta+\varepsilon\)。本轮只做经验检验，不做定理推广。

## 4. 可微实现（对草案 L1 的工程化收窄）

草案的 \(\mathcal L_{\text{cons}}\) 直接作用于不可微的 \(\rho_d\)。本轮用可微代理：令 \(r\) 为不含敏感信息的安全响应（R-TOFU `idontknow.jsonl` 语料），\(q_d(x)\) 为策略 \(d\) 的 prompt 前缀，

\[
n_d(\theta)= -\frac{1}{|r|}\sum_t \log p_\theta(r_t\mid q_d(x), r_{<t}),\qquad
\mathcal L_{\text{inv}}=\underbrace{\frac{1}{|\mathcal D|}\sum_d n_d}_{\text{所有策略下都拒答}}
+\lambda\underbrace{\frac{1}{|\mathcal D|}\sum_d (n_d-\bar n)^2}_{\text{一阶一致性：压平策略差}}
+\beta\,\mathcal L_{\text{retain}}
\]

\(\mathcal L_{\text{retain}}\) 为保留集上 gold answer 的 NLL（防止把模型训成"一律拒答"）。这是草案 L1 的 SFT 版替代：不追求严格的 IRM 梯度对齐，换取稳定性与单卡可跑性。**IRM/DRO/TV 证书（草案 L2/L3、路线 C）本轮不实现**，列为后续工作。

训练用 LoRA（r=8, α=32）在 `LRM-target` 上微调，避免全参 8B 训练的成本与灾难性遗忘。

## 5. 审计证书（路线 A，最小版）

对每个策略取 \(n_d\) 个样本，\(\hat\rho_d\) 为经验泄漏率，\(\widehat\Gamma\) 为经验鸿沟：

\[
\rho_d(\theta)\le \hat\rho_d+\sqrt{\tfrac{\ln(1/\delta)}{2n_d}}+\widehat\Gamma,\quad \forall d\in\mathcal D
\]

以至少 \(1-\delta\) 概率成立（Hoeffding，要求样本独立有界）。**注意**：本轮样本量小（n≈24–40），且 \(\widehat\Gamma\) 本身是估计量，界会很松；只报告覆盖率与保守性，不宣称"已证明安全"。

## 6. 与既有工作的差异化（检索层面，待深度核验）

- R-TOFU (EMNLP 2025) 揭示 CoT 轨迹泄漏，但其指标沿默认生成路径；本工作把**解码策略本身**作为自变量。
- R2MU / CiPO / GUARD / STaR 类工作改进遗忘目标或轨迹质量，未检验跨推理预算的不变性。
- ICML 2025「Invariance Makes LLM Unlearning Resilient…」的不变性轴是**下游微调**，不是解码策略。
- SEGUE (ACL 2026) 是推理时熵引导解码干预，属"测/挡"，不是训练约束 + 证书。
- conformal / probabilistic 界为遗忘提供统计保证，但对象是参数/数据影响，非解码策略谱。

## 7. 主要风险（执行者自审，非跨模型评审）

1. **策略前缀本身可能诱导拒答**：`ZeroThink` 的空 `<think>` 块是分布外前缀，基线"泄漏回升"可能部分来自 prompt 偏移而非知识残留 → 必须同时报告 target 模型在同样前缀下的表现作为对照。
2. **全拒答退化**：不变性目标可能让模型对所有问题都拒答 → 保留集 ROUGE-L 与真实答案命中率是硬性护栏。
3. **实体抽取器偏差**：以 gold answer 中最长大写短语作为敏感实体，可能误抽 → 同时报 ROUGE-L 连续指标并抽检输出文本。
4. **样本量**：`forget01` 中 `task_id==1` 仅 40 条，统计功效有限 → 结论限定为 pilot 信号。
5. **证书过松**：Hoeffding + 估计鸿沟在小 n 下几乎必然覆盖，覆盖率高不等于有用 → 报告界的宽度而非只报覆盖率。

## 8. Reviewer 状态

`REVIEW_UNAVAILABLE`：本环境无跨模型评审后端（无 Codex MCP、`reviewer.json`、`reviewer_route.py`），`/research-review`、`/experiment-bridge` 的 cross-model code review 均未执行。上述风险为执行者自审，**不得**作为独立评审结论写入论文。


## 补充：LLM-as-judge 已启用（2026-11-23）

用户提供了 Hy4 OpenAI 兼容端点（`/usr/local/workspace/.env`），已实现 `code/llm_judge.py`。
§7 风险 3（实体抽取器偏差）因此得到第二套指标交叉验证；但 hy4 与执行者同家族，
**不能**解除 §8 的 `REVIEW_UNAVAILABLE`，也不能产生证据门控回执。详见
`idea-stage/batch2/LLM_JUDGE_INTEGRATION.md`。
