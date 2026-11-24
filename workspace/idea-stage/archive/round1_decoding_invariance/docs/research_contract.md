# Research Contract — 解码不变性遗忘

> 生成时间：2026-11-23
> 来源：`workspace/idea-stage/idea-1.md`（DESIGN DRAFT，未经跨模型评审）
> 状态：**ACTIVE**（本次 idea-discovery → experiment-bridge 的聚焦工作契约）
> 说明：`templates/RESEARCH_CONTRACT_TEMPLATE.md` 在本环境不可用，本文件按契约必需字段手工实例化，字段含义保持一致。

## 1. 选中的 Idea 与选择理由

- **Idea 1：解码不变性遗忘 + 可审计证书**（Decoding-Invariant Unlearning, DIU）
- 选择理由：用户已指定该 idea 作为本轮自动科研输入；它同时具备 (a) 可被现有 R-TOFU 资产直接检验的诊断性假设（"假遗忘"），(b) 可在一张 H20 上 2 小时内完成的最小判别实验，(c) 与既有 D3/SpecGap 审计资产的潜在缝合点。未重新生成 8–12 个候选 idea，因为本轮输入是指定草案而非宽泛方向。

## 2. Problem Anchor（防止范围漂移）

> 现有 LRM 遗忘方法只在**默认推理路径**上评估与优化遗忘；若被遗忘知识在**少推理/零推理**等其它解码路径上复活，则"遗忘"不成立。我们只研究：**遗忘效果是否对解码策略（推理预算谱）不变，以及如何训练并审计这种不变性。**

不研究的：新 benchmark 构建、新的偏好优化算法、跨任务通用安全对齐、对任意未知 prompt 攻击的绝对保证。

## 3. Core Claims（待验证，非结论）

- **C1（诊断）**：已有 R2MU 类已遗忘检查点在 `DefaultCoT` 下泄漏率低，但在 `ZeroThink`/`LessThink` 下显著回升，即存在"假遗忘"，遗忘鸿沟 \(\Gamma=\max_d\rho_d-\min_d\rho_d\) 显著大于 0。
- **C2（方法）**：把解码策略当作"环境"，在训练目标中加入跨策略一致性正则，可在保留集效用不明显下降的前提下压平 \(\Gamma\) 并降低最坏策略泄漏率。
- **C3（证书）**：有限策略集上的 Hoeffding 上界 + 估计鸿沟可给出"任意已测策略泄漏率不超过 X"的高置信审计证书；连续预算上的 Lipschitz 版本为开放项。

## 4. Minimum Convincing Evidence

| Claim | 最小判别证据 | 失败判据 |
|---|---|---|
| C1 | `r2mu-forget01` 在 ≥3 个策略上测 \(\rho_d\)，\(\Gamma\ge0.15\) 且 \(\rho_{\text{Zero}}-\rho_{\text{Default}}\ge0.10\) | 曲线平坦 → 核心假设被否证，转 informative negative |
| C2 | 不变性训练模型 vs 单策略对照：`\Gamma_{\text{ours}}\le0.10` 且 \(\max_d\rho_d\) 低于基线 ≥0.20；保留集 ROUGE-L 下降 ≤0.10 |  ours 与对照无差异 → 不变性正则无效 |
| C3 | 在留出策略/预算网格上，实测泄漏率被证书上界覆盖比例 ≥ \(1-\delta\)（δ=0.1） | 覆盖率不足 → 证书形式需修正 |

**评测纪律**：泄漏判定必须相对数据集真实 gold answer（含其中的专有实体），不得使用另一个模型的输出作为 ground truth；所有方法使用同一批样本、同一阈值、同一生成参数。

## 5. 不变式与边界

- 所有代码、日志、结果写入 `/usr/local/workspace/R-TOFU/workspace/`；数据与模型只读自 `/jizhicfs/chenyliao/` 子目录。
- 随机种子固定；结果以 JSON/JSONL 落盘；任何数字必须可追溯到具体结果文件。
- 未核验的 arXiv 编号不写入；引用仅作定位时明确标注"待核验"。

## 6. Next Step

→ `refine-logs/EXPERIMENT_PLAN.md` → `/experiment-bridge` → `/auto-review-loop`（本环境缺评审后端时不得宣称通过评审门控）。
