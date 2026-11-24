# LLM-as-judge 接入说明（2026-11-23）

## 用户提供的配置

`/usr/local/workspace/.env` 中的 `Hy4_TOKEN` 对应 OpenAI 兼容端点：
`POST https://tokenlink.woa.com/openapi/v1/chat/completions`，`model: hy4`。
已实测 `HTTP 200`、返回 `choices[0].message.content`。

**凭据处理**：`code/llm_judge.py` 运行时从 `.env`/环境变量读取 token，
不打印、不写入任何结果文件、不进入仓库；本报告不记录 token 值。
`.env` 原文件保持不动。

## 用途与边界

| 用途 | 是否使用 Hy4 | 说明 |
|---|---|---|
| 实验指标：软泄漏判分 ℓ(â,z;s) | ✅ | 判分器接收**数据集 gold answer** 作为真值，只判断生成文本是否泄漏；绝不用模型输出当 ground truth |
| 跨模型独立评审 `/research-review` | ❌ | hy4 与执行者同属 Hunyuan 家族；按 ARIS 纪律同家族评审只能 provisional，不能产生 `accept` 回执 |
| 证据门控 `gates.idea-discovery-evidence` | ❌ | 仍缺 `run_state.py` / `idea_discovery_gate.py`，保持 `BLOCKED` |

因此 **`REVIEW_UNAVAILABLE` / `BLOCKED` 结论不变**；新增的只是评测指标。

## 实现

- `code/llm_judge.py`：读 `results/eval_<tag>.jsonl`，按 (策略, forget/retain) 分组抽样；
  并发调用 Hy4（`temperature=0`，超时 90s，重试 3 次），要求返回严格 JSON
  `{"leak":0|1,"confidence":0-1,"reason":"..."}`；解析失败记 `judge_ok=0` 并保留错误。
- 输出：`results/judge_<tag>.jsonl` + `judge_<tag>.summary.json`
  （含 LLM 泄漏率、与实体规则的一致率、Γ_LLM）。
- `code/analyze_results.py`：自动把 judge 结果并入 `EXPERIMENT_RESULTS.md` / `ANALYSIS.md`。
- `code/recompute_leak.py`：修正实体抽取器（去掉 `Author ` 前缀与所有格 `'s`）后重算
  `entity_leak`，原值保留在 `entity_leak_raw` / `key_phrase_raw`，可审计。

## 兼容性踩坑（已验证）

- 该端点**不接受** `max_tokens` 字段：传入后 `content` 为空，判分全部失败；已移除。
- 短超时（45s）+ 高并发会超时；改为 90s / 并发 3，小样本验证 4/4 成功。
- 提示词必须显式写「gold answer 是数据集真值、不是模型输出」，避免判分器把参考答案当作可泄漏文本。

## 对结论的影响

LLM 判分能捕捉**改写、部分专名、CoT 内部泄漏**，弥补字符串匹配的漏检；
但它与执行者同家族，判分结果只作为**第二套指标**与一致性交叉验证，
不提升证据等级到「独立评审通过」。

## 运行实测补充（同日）

Hy4 端点对长生成文本响应**不稳定**：实测单条 900–3000 字符输入耗时 33–117s，
部分请求在 45–60s 超时；这是服务端延迟，不是输入长度单调决定。处理方式：

- 判分输入截断到 600 字符（泄漏判定所需信息通常位于开头），超时 35s、重试 1 次、并发 8。
- 先完成 `ctrl-single` / `ours-inv` 两个系统（16 样本/策略，全部判分成功）；
  其余 3 个系统改为 8 样本/策略补跑。样本数差异在 `judge_*.summary.json` 的
  `limit_per_group` 与结果表「判分数」列中显式标注，不做隐式补齐。
- 解析失败或超时的样本 `judge_ok=0`、`llm_leak=null`，**保留在 JSONL 中并计入 `failed`**，
  不删除、不填 0；`llm_leak_rate` 只用成功样本计算。
- 结论口径：LLM 判分与实体规则并列展示一致率；若失败率高，则明确写「判分功效不足」，
  不得用成功样本的偏倚结果替代全量结论。

**已知限制**：判分器与执行者同家族，判分结果只作第二套指标；
不解除 `REVIEW_UNAVAILABLE` / `BLOCKED`。

## 最终判分结果（2026-11-23）

| 系统 | 抽样/策略 | Γ_LLM | 说明 |
|---|---|---|---|
| target | 8 | 0.000 | **LOW_POWER**：32 个样本仅 8 个判分成功，ZeroThink 0/8，结果不可用 |
| r2mu01 | 8 | 0.333 | DefaultCoT 2/8、LessThink 3/8 失败；Γ_LLM > 实体规则 Γ=0.050，提示规则漏检 |
| r2mu05 | 8 | 0.000 | 32/32 成功 |
| ours-inv | 16 | 0.000 | 64/64 成功，与实体规则一致率 1.0 |
| ctrl-single | 16 | 0.000 | 64/64 成功，与实体规则一致率 1.0 |

**解释**：LLM 判分发现了字符串匹配漏掉的部分名字泄漏，因此「实体规则 = 0」不等于「无泄漏」；
但失败样本与小 n 使 Γ_LLM 只能作定性提示，不能作为 S1 的翻案证据。
最终判据仍为 S1/S2/S3 FAIL、S4 PASS（界松）。
