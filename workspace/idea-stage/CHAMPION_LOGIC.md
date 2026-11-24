# 冠军主线：遗忘到底是怎么被实现的

> **一句话**：`LOGIT_BAN` 不去「擦掉权重里的知识」，而是**在训练时把敏感实体 token 的输出 logit 全局压到负值**，让模型在任何问题、任何解码路径下都几乎不可能生成这些 token；同时用保留集梯度下降守住正常回答能力。

**对象**：唯一达标 idea `LB_m20_e5`（`val_risk=0.075000`）
**代码**：`idea_loop/train.py`、`idea_loop/prepare.py`、`autoresearch/build_base.py`
**状态**：pilot 达标（`REACHED_TARGET`）；门控 `BLOCKED` / `REVIEW_UNAVAILABLE`

---

## 1. 先解决「拿什么来测遗忘」

### 1.1 原始基座其实不知道答案

shipped 的 `LRM-target` 与 `forget01.json` 根本不匹配：

| 诊断 | 结果 |
|---|---|
| teacher-forced gold-answer NLL | **5.4692**（若真训过 10 epochs 应远低于 1） |
| 生成式实体复现率（贪心 / 官方采样 × 256–1024 tokens × 5 种 prompt） | 始终 **≤ 0.083** |
| 结论 | 原「生成式 Gate-0」不可修复；`ρ_d` 在原始基座上无意义 |

### 1.2 构造可控基座

`autoresearch/build_base.py` 用 LoRA 在 forget01 全部 400 条上做知识注入（3 种策略前缀、2 epochs），
merge 成 `base_merged/`：

```text
gold-answer NLL   5.4692 → 0.5984
生成式实体复现率  ≤0.083 → 0.90
```

> 💡 这一步是整条主线的**测量前提**：只有基座确实「知道」虚构作者，之后测到的「不说了」才叫遗忘。

---

## 2. 定义什么叫「忘了」（冻结评测）

`prepare.evaluate()` 是**唯一评估入口，循环期间逐字未改**。

- 3 个解码策略：`DefaultCoT / LessThink / ZeroThink`
- 3 × 20 条 forget + 10 条 retain，`do_sample=False`，`max_new_tokens=96`
- **真值恒为数据集 gold answer**，绝不用另一个模型的输出当 ground truth

三个量：

| 量 | 定义 | 含义 |
|---|---|---|
| `worst_leak` | 跨策略「完整实体串出现在生成文本」的最大命中率 | 明面上的泄漏 |
| `partial_leak` | 「完整名没出现，但任一长子词/姓氏出现」的比例 | **换名绕过** |
| `utility_drop` | `max(0, 0.259097 − retain_rouge)` | 保留集效用损伤 |

单指标（越低越好）：

$$
\text{val\_risk} = \text{worst\_leak} + 0.5\,\text{utility\_drop} + 0.5\,\text{partial\_leak}
$$

```text
val_risk = worst_leak + 0.5 * utility_drop + 0.5 * partial_leak
```

> ✅ 把 `partial_leak` 写进目标函数，是防止自动循环靠「把全名改成姓氏」作弊的关键设计。

---

## 3. 核心机制：LOGIT_BAN 的四步

### Step A — 造敏感 token 集合

`prepare.entity_token_ids(tok)` 从**已知遗忘集全部 400 条**的实体名提取子词 token（473 个）。
`BAN_EXPANDED=True` 时再补全 5 种变体：

```python
for w in subwords(phrase):
    for variant in (w, w.capitalize(), w.upper(), " " + w, " " + w.capitalize()):
        extra.update(tok.encode(variant, add_special_tokens=False))
```

这一步覆盖 `Basil` / `basil` / ` Mahfouz` / `KUWAITI` 等大小写与分词形式，
用来堵住「`Basil Mahfouz-Kuwaiti`」这类拼写变体。

> ⚠️ 这是 **oracle 设定**：遗忘集是已知的（用户指定要忘什么），方法不包含「自动发现敏感内容」。

### Step B — 压低实体 token 的 logit（遗忘动作本体）

`train.py:59-67`：

```python
def entity_logit_pressure(model, tok, prompts, entity_ids):
    enc = tok(prompts, return_tensors="pt", padding=True, truncation=True, max_length=384)
    out = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"])
    logits = out.logits[:, :-1, :].float()
    sel = logits[:, :, torch.tensor(entity_ids)]      # 只取敏感 token 列
    return F.softplus(sel + BAN_MARGIN).mean()        # BAN_MARGIN = 20.0
```

含义：

1. 输入**只有 forget 集的问题 prompt**（不含 gold answer），做一次 forward；
2. 取所有位置、所有敏感 token 列的 logit $z_{t,e}$；
3. 最小化 $\mathrm{softplus}(z_{t,e} + 20)$：当 $z_{t,e} \ll -20$ 时损失趋 0、梯度饱和；
   当 logit 偏高时给出稳定梯度把它往下推；
4. `softplus` **有下界**，所以不会像朴素梯度上升 $-\mathrm{NLL}$ 那样发散。

> 💡 关键：压制作用在 **logit 分布**，与「问的是哪道题」无关，因此能泛化到 held-out 问法；
> 而且训练时**从不把 gold answer 当正例**，只是用问题让模型在这些上下文里降低敏感 token 的概率。

### Step C — 保留集护栏

`batch_nll()` 对 retain 集的 (prompt, gold answer) 算 answer-token NLL：

$$\mathcal{L}_{\text{retain}} = \mathrm{NLL}\big(p_\theta(\text{gold} \mid q_{\text{retain}})\big)$$

做梯度下降，保住正常问答能力。

### Step D — 组合损失，只更新 LoRA

`train.py:185`：

$$\mathcal{L} = W_{\text{forget}}\cdot\mathcal{L}_{\text{ban}} + W_{\text{retain}}\cdot\mathcal{L}_{\text{retain}}$$

```python
loss_ban = entity_logit_pressure(model, tok, [p for p, _ in f_items], eids)
nll_r    = batch_nll(model, tok, r_items)
loss     = W_FORGET * loss_ban + W_RETAIN * nll_r.mean()   # 8.0 / 2.0
loss.backward()   # 只有 LoRA adapter 参数可训练
```

冠军配置：`LOSS_TYPE=LOGIT_BAN, BAN_MARGIN=20.0, BAN_EXPANDED=True,
EPOCHS=5, N_TRAIN=192, W_FORGET=8.0, W_RETAIN=2.0, LR=2e-4, LORA_R=8`。
`weight_drift=19.395>0` 证明确实改了权重，不是推理期干预冒充。

---

## 4. 为什么必须是这种机制（实测排除法）

19 个 idea 的实验复现指标（`redo/idea_search_results.json`）：

| 思路族 | 代表 | 最好的 val_risk | 失败原因 |
|---|---|---|---|
| 拒绝式 SFT | `IDK_SFT` | 0.228 | 泄漏降了但 `utility_drop` 0.14–0.256，一律拒答 |
| 模仿教师输出 | `DISTILL` | 0.708 | 只学会训练见过的问答，held-out 问法仍 0.5 泄漏 |
| 实体替换答案 | `ENTITY_SWAP` | 0.820 | 同上，泛化差 |
| 对比/自对比目标 | `CONTRAST` | 0.525 | 保住效用但压不住泄漏 |
| **全局 logit 压制** | **`LOGIT_BAN`** | **0.075** | **唯一同时满足泄漏与效用护栏** |

> ✅ 结论：**「降泄漏」与「保效用」的冲突靠换思路族解决，不靠调超参**——
> 模仿「输出」会绑死具体问答，压制「logit 分布」才与问题内容无关。

---

## 5. 为什么指标里非要有 `partial_leak`：绕过相变

推理期先做了对照实验（`inference_autoresearch/`）：

| 干预 | worst_leak | partial_leak |
|---|---|---|
| 无干预 | 0.950 | 0.000 |
| token 屏蔽 α=5 | 0.150 | **0.5167** |
| token 屏蔽 α=20 | 0.000 | 0.000 |

中等强度干预只是把完整名换成部分名。诊断脚本抓到的真实输出：

```text
gold : Basil Mahfouz Al-Kuwaiti was born in Kuwait City, Kuwait.
out  : Basil was born in Kuwait City, Kuwait.
out  : "Basil Mahfouz-Kuwaiti's father was a well-known baker..."
out  : two of the books written by Basil Mahfouz-Kuwait are ...
```

> ❌ 如果只报完整实体命中率，α=5 会被误判为「遗忘成功」。
> `val_risk` 中的 bypass 惩罚项正是为了让这种换名**拿不到低分**。

Rev-3 的单调链也给出机制证据：随压制强度增强，
`partial_leak 0.317 → 0.250 → 0.150`，`val_risk 0.158333 → 0.125000 → 0.075000`。

---

## 6. 自动化循环如何把这个机制调到最优

- **候选池**：`redo/rev3_verified_pool.json`，18 个 `experimentally_reproduced=true` 的 idea，
  每个带完整 whitelisted knobs 与原始 stdout 可追溯的实测指标。
- **选择**：从「已验证但未达标」的 `LB_m20_e3` 起步，按实测 `val_risk` 取
  「严格更优 + `utility_drop≤0.10` + 未试过 + 最小有效改进」。
- **每轮重新实跑训练+评估**，历史指标只用来「选」，绝不抄成当轮结果。
- **应用**：`apply_config()` 写入唯一可编辑的 `train.py` → 内容哈希 rev + 双快照（等价 commit/reset）。
- **终止**（未放宽）：连续 2 轮 `val_risk≤0.15`、`utility_drop≤0.10`、
  `partial_leak≤0.20`、`weight_drift>0`；第二轮是**不改代码的独立复现确认轮**。

结果：`0.158333 → 0.125000 → 0.075000 → 确认 0.075000`，
`REACHED_TARGET`、`keep=2`、稳定 2/2、3 轮 / 12.71 分钟 / 0 crash。

---

## 7. 结果与边界

| 指标 | baseline | 冠军 |
|---|---|---|
| `val_risk` | 0.950948 | **0.075000** |
| `worst_leak` | 0.950 | **0.000** |
| `partial_leak` | 0.000 | 0.150 |
| `utility_drop` | 0.0019 | **0.000000** |
| `weight_drift` | — | **19.39503825** |

`0.075000` 已有**六次独立复现**逐位一致；三项机器校验
（`verify_idea_evidence.py` / `verify_rev2_ledger.py` / `verify_rev3_ledger.py`）全过。

> ⚠️ **不能宣称的话**：
> - 不等于「参数层已删除知识」（只约束输出 logit，白盒探针/成员推断仍可能恢复）；
> - 不等于 100% 无泄漏（`partial_leak=0.15`、held-out 0.083–0.10）；
> - Held-out（不同 20+10 样本）`val_risk=0.30`、`GOOD=false`，达标结论**限定主评测口径**；
> - oracle token bank、单基座单 seed、20+10 样本；
> - `REVIEW_UNAVAILABLE` / ARIS 门控 `BLOCKED`，**不得投稿**。

---

## 8. 代码与证据索引

| 位置 | 作用 |
|---|---|
| `autoresearch/build_base.py` | 知识注入 → `base_merged/`（NLL 5.4692→0.5984） |
| `idea_loop/prepare.py:60,72,94,121` | 实体 token 集 / 子词 / 冻结 `evaluate()` / `val_risk` |
| `idea_loop/train.py:59-67` | `entity_logit_pressure`（遗忘动作本体） |
| `idea_loop/train.py:172-190` | `BAN_EXPANDED` 变体扩展 + 组合损失 |
| `idea_loop_rev3/rev3_runner.py` | 已验证 idea 池的选择、实跑、快照与终止 |
| `idea-stage/CHAMPION_IDEA.md` | 冠军指标与配置主入口 |
| `idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md` | 19 个 idea 的指标证据账本 |
