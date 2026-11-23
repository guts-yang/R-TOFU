# Idea 1 方法设计：解码不变性遗忘 + 可审计证书

**状态**: 设计草案（DESIGN DRAFT）。本文件给出叙事骨架与数学框架，所有公式与命题为待验证构造，尚未经跨模型评审或实测。
**关联**: `idea-stage/IDEA_REPORT.md` 的 Idea 1；承接用户既有 D3/SpecGap 审计资产。
**日期**: 2026-11-23

---

## 一、故事怎么讲

### 1.1 叙事定位（结构缺口 lens）

用 idea-creator 的结构缺口透镜给故事定位，增强理论站位：

- **untested-assumption**：所有 LRM 遗忘方法（R2MU/CiPO/FRUL/GUARD/STaR）都隐含假设"遗忘是默认 CoT 路径下的属性"，无人检验它对其他解码路径是否成立。
- **diagnostic**：没人问过"泄漏率作为推理预算的函数长什么样"——这个问题一旦问出，假遗忘立刻现形。
- **contradiction**：同一模型，DefaultThink 说"忘了"，ZeroThink 说"没忘"——两个都为真的观测构成冲突，必须被一个统一理论解释。
- **method-transfer**：把域泛化里的不变风险最小化（IRM）与分布鲁棒优化（DRO）迁移到"解码策略泛化"这一新维度。

### 1.2 六幕叙事

| 幕 | 内容 | 目的 |
|---|---|---|
| 1 钩子 | 一张对比图：埋掉的敏感知识，换个问法（少推理/不推理）就复活。R-TOFU 已观察到该现象，不是假想敌。 | 10 秒抓住审稿人 |
| 2 矛盾 | 现有方法优化目标各异，却共享同一盲点：只在默认路径上忘。LRM 与普通 LLM 的本质区别正是"同一问题存在整条推理预算谱"。 | 立结构裂缝 |
| 3 洞察 | 把遗忘重述为普适性质：无论用户让模型思考多久，被遗忘的知识都不该出现。类比"加密不能只防一种钥匙"。 | 从 benchmark 技巧升为隐私原则 |
| 4 方法 | 把解码策略当"环境"施加不变性约束，关闭所有短路通道；顺势给出跨策略泄漏上界证书。 | 方法 + 高潮同帧 |
| 5 证据 | 一张会分叉的曲线：基线右端翘起（被识破），本方法压平。注意该形状目前是**预期**，需 pilot 坐实。 | 图驱动 |
| 6 升华 | 从"测出来"（把解码陷阱当评测指标）到"保证不会"（当训练约束 + 审计证书）。 | 范式转变收尾 |

### 1.3 方法先行（idea-creator Phase 6 要求：先讲做什么，再讲宣称什么）

1. 选定一个待遗忘的 LRM（如 DeepSeek-R1-Distill-8B）和 R-TOFU 的敏感问答集。
2. 定义一组解码策略（默认/少推理/零推理/摘要），把它们当作多个"环境"，每个环境下测量目标知识的泄漏率。
3. 训练时同时压低所有环境的泄漏率 **并** 惩罚环境间的泄漏差（一阶一致性为主，IRM/DRO 为理论升级版），同时约束保留集上的通用推理能力不退化。
4. 输出一张证书：以高置信度声明"对任意解码策略，泄漏率不超过 X"。

故事的一句话 closes：**我们让遗忘不再依赖用户怎么问。**

```mermaid
flowchart LR
    A[钩子: 换个问法知识复活] --> B[矛盾: 所有人只堵默认路径]
    B --> C[洞察: 遗忘须对整条推理预算谱不变]
    C --> D[方法: 解码策略当环境 + 不变性约束]
    D --> E[证书: 任意策略泄漏上界]
    E --> F[升华: 从检测到可证明防御]
```

---

## 二、数学公式设计

### 2.1 符号

- $\theta$：模型参数，$\theta_0$：遗忘前初始参数。
- $x$：关于目标敏感知识 $s$ 的提问；$D_f$：遗忘集；$D_r$：保留集。
- 解码策略 $d\in\mathcal D=\{$DefaultThink, LessThink, ZeroThink, SummaryThink$\}$，对应推理轨迹长度预算。
- 策略 $d$ 下的生成：轨迹 $z\sim p_\theta(z\mid x,d)$，答案 $\hat a\sim p_\theta(\hat a\mid x,z,d)$；ZeroThink 对应 $z=\varnothing$，即 $p_\theta(\hat a\mid x)$。
- 泄漏指示 $\ell(\hat a,z;s)\in\{0,1\}$：轨迹或答案中是否出现 $s$ 或其可识别改写（软版本可用判别器/NLI 打分）。

### 2.2 核心量：解码条件泄漏率与遗忘鸿沟

$$
\rho_d(\theta)\;=\;\mathbb E_{x\sim D_f,\;z\sim p_\theta(\cdot\mid x,d),\;\hat a\sim p_\theta(\cdot\mid x,z,d)}\big[\,\ell(\hat a,z;s)\,\big]
$$

定义**遗忘鸿沟**（要消灭的量，即"假遗忘"的度量）：

$$
\Gamma(\theta)\;=\;\max_{d\in\mathcal D}\rho_d(\theta)\;-\;\min_{d\in\mathcal D}\rho_d(\theta)
$$

假遗忘现象的形式化：$\rho_{\text{default}}(\theta)\approx 0$ 但 $\Gamma(\theta)$ 很大。

### 2.3 核心命题（故事的"定理"）

**命题 1（不变性 ⇒ 鲁棒遗忘）**：若训练后满足 $\Gamma(\theta)\le\varepsilon$ 且 $\min_{d}\rho_d(\theta)\le\delta$，则对所有策略 $d\in\mathcal D$：

$$
\rho_d(\theta)\;\le\;\delta+\varepsilon
$$

*证明*：$\rho_d(\theta)\le \min_{d'}\rho_{d'}(\theta)+\Gamma(\theta)\le\delta+\varepsilon$。∎

意义：把"某一策略下忘掉 + 策略间一致"直接升级为"所有策略下都安全"。这是把训练目标与审计保证连起来的关键一步。

### 2.4 不变性目标：三个层级（由简到繁，主方法用 L1）

**L1 一致性正则（主方法，简单稳定）**

$$
\mathcal L_{\text{cons}}(\theta)\;=\;\frac{1}{|\mathcal D|}\sum_{d\in\mathcal D}\rho_d(\theta)\;+\;\frac{\lambda}{|\mathcal D|^2}\sum_{d,d'\in\mathcal D}\big(\rho_d(\theta)-\rho_{d'}(\theta)\big)^2
$$

第一项确保所有策略都低，第二项压 $\Gamma$。先用它做 pilot；IRM 式 penalty 在 LLM 上 notoriously 不稳定，不作为主方法。

**L2 IRM 式梯度对齐（抓表示层短路，理论升级版）**

令 $\Phi_\theta(x,z)$ 为共享表示，$w$ 为"是否含目标知识"的线性探针头：

$$
\mathcal L_{\text{IRM}}(\theta,w)\;=\;\sum_{d\in\mathcal D}\mathcal L_d\big(w\circ\Phi_\theta\big)\;+\;\lambda\Big\|\nabla_w\,\mathcal L_d\big(w\circ\Phi_\theta\big)\Big|_{w=w_0}\Big\|^2
$$

不变性迫使各解码策略学到同一个"知识方向"，于是对任一策略切断该方向，对所有策略生效。这是"短路通道"假说的直接算子化。

**L3 分布鲁棒优化（DRO，证书友好）**

$$
\min_\theta\;\max_{d\in\mathcal D}\mathcal L_d^{\text{forget}}(\theta)\quad
\text{s.t.}\quad \mathbb E_{x\sim D_r}\mathcal L_{\text{retain}}(\theta,x,d)\le\tau,\;\forall d\in\mathcal D
$$

直接优化最坏策略，天然给出"对所有策略成立"的保证。

### 2.5 总目标与保留侧

$$
\mathcal L\;=\;\mathcal L_{\text{forget}}\;+\;\lambda_{\text{cons}}\mathcal L_{\text{cons}}\;+\;\beta\,\mathcal L_{\text{retain}}\;+\;\gamma\,\mathcal L_{\text{qual}}
$$

- $\mathcal L_{\text{retain}}$：在 $D_r$ 上跨所有策略计算的推理保持损失（GSM8K/MATH/MMLU）。
- $\mathcal L_{\text{qual}}$：轨迹结构质量项（可接 GUARD 的 NFRS 负向项或流畅度）。

### 2.6 审计证书设计（故事高潮，三条路线）

**路线 A：有限策略集上的高置信证书（先做，最易落地）**

给定每策略 $n_d$ 个样本，Hoeffding 界给出单策略上界，再加估计的鸿沟：

$$
\rho_d(\theta)\;\le\;\hat\rho_d+\sqrt{\frac{\ln(1/\delta)}{2n_d}}+\widehat\Gamma,\quad \forall d\in\mathcal D
$$

以至少 $1-\delta$ 概率成立。输出即一张"任意策略泄漏不超过右端"的审计证书。

**路线 B：连续推理预算上的 Lipschitz 证书**

把策略推广为连续预算 $\ell\in[\ell_{\min},\ell_{\max}]$，若 $\rho_\ell$ 关于 $\ell$ 为 $K$-Lipschitz（$K$ 可经验估计或用谱范数界定），取步长 $h$ 的网格：

$$
\sup_{\ell\in[\ell_{\min},\ell_{\max}]}\rho_\ell(\theta)\;\le\;\max_{i}\rho_{\ell_i}(\theta)+\frac{K h}{2}
$$

覆盖"任意思考长度"，而非仅 4 个离散策略。

**路线 C：迁移 SpecGap 的 TV 界到策略间（与用户审计资产缝合最紧）**

$$
\big|\rho_d(\theta)-\rho_{d'}(\theta)\big|\;\le\;\mathrm{TV}\big(p_\theta(\cdot\mid x,d)\,\|\,p_\theta(\cdot\mid x,d')\big)
$$

训练时压平策略间的输出分布 TV 距离，证书余项自动变小。这条路让 Idea 1 与 D3/SpecGap 长成一条线，是"证书"故事最独特的部分。

**命题 2（证书有效性，待证）**：在路线 A/B 的置信结构下，证书上界以至少 $1-\delta$ 概率覆盖任意策略的真实泄漏率。严格化需引入解码策略到泄漏率的敏感度分析，列为开放项。

---

## 三、最小判别实验（坐实故事第 5 幕的曲线形状）

- 模型：DeepSeek-R1-Distill-8B（或同等可本地部署的 LRM）。
- 数据：R-TOFU forget01 / 05 / 10；保留侧 GSM8K + MMLU。
- 策略：$\mathcal D$ 中 4 个；额外扫 $\ell$ 网格验证路线 B。
- 基线：R2MU、Reasoned IDK、CiPO、FRUL、GUARD、R-TOFU 原方法。
- 主图：$\rho_d$（纵轴）vs 解码策略（横轴）——基线右端翘起，本方法压平。
- 判据：若基线在 ZeroThink 的 $\rho$ 显著回升而本方法不回升 → 假设成立；否则按"核心假设被否证 / informative negative / pilot 效能不足"分类。
- 证书校验：实测泄漏被证书上界覆盖的比例是否 $\ge 1-\delta$。
- 算力：单卡 8B、2-3 小时；本机 `cuda=False`，标注 `needs manual pilot`，须在服务器执行。

---

## 四、诚实声明

- 所有公式为设计构造，符号与命题尚未经跨模型评审；命题 2 的正确性待严格证明。
- 引用仅作定位（R-TOFU/R2MU/CiPO/FRUL/GUARD/STaR/D3-SpecGap），未核验的精确 arXiv 编号不在此写入，遵循不编造原则。
- 本文件是 Idea 1 的深化草案，不是通过完整 idea-creator 门控的验证结论（环境缺 reviewer MCP / GPU / helper）。
