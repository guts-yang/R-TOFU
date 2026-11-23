# 自动重做报告 — Gate-0/1/2/3 + autoresearch + integrity forensics

**日期**: 2026-11-23
**触发**: 用户要求「按照建议自动重做，并且自动研究」（`/autoresearch-loop` + `/anti-autoresearch`）
**代码根**: `workspace/redo/`、`workspace/autoresearch/`（独立 git 仓库）
**取证目录**: `workspace/audit_paper/`

---

## 1. Gate 逐项结果

| Gate | 上一轮状态 | 本轮结果 | 判定 |
|---|---|---|---|
| **Gate-0 基座可复现** | FAIL（生成式复现率 ≈0） | 定位到根因后**重定义并通过** | ⚠️ 有条件通过 |
| **Gate-1 无系统性截断** | FAIL（`truncated_rate≈0.95`） | teacher-forced 路径 `truncated_rate=0.0` | ✅ 主指标通过 |
| **Gate-2 保留效用护栏** | FAIL（retain ROUGE 0.180→0.013） | GA+GD 下 retain NLL 1.4807 ≤ 基线 1.5857 | ✅ 通过（但有重叠偏差） |
| **Gate-3 MCS 对照** | 未做 | 已报告跨策略 gap γ | ✅ 已实现 |

### Gate-0 的关键诊断（决定性发现）

`redo/gate0_probe.py` 与 `redo/teacher_force_check.py` 的实测：

- 贪心 / 官方采样（`temperature=0.6, top_p=0.95`）× 256/512/1024 token ×
  5 种 prompt（DefaultCoT / LessThink / ZeroThink / plain / chat），
  基座实体复现率**始终 ≤ 0.083**；加大 token 预算无效。
- teacher-forced gold-answer NLL = **5.4692**（probe 另一批样本 4.176）。
  若真在 R-TOFU QA 上微调过 10 epochs，该值应远低于 1。
- **结论**：`models/sangyon/LRM-target` 与这批数据**根本不匹配**；
  不是解码参数问题，因此原「生成式 Gate-0」无法修复。

**结构性 pivot（Round 2 建议的落地）**：
1. 用 `autoresearch/build_base.py` 做一次性 LoRA 知识注入（forget01 全部 400 条、
   3 种策略前缀、2 epochs、64.9s），merge 出可复现基座 `base_merged/`；
   gold NLL **5.4692 → 0.5984**，通过重定义的 Gate-0（阈值 ≤1.5）。
2. 主指标从生成式 ρ_d 改为 **teacher-forced 泄漏似然** `leak_d = exp(-NLL_d)`，
   固定评测口径写在 `autoresearch/prepare.py`（循环期间冻结）。
3. 训练/评测划分：遗忘训练只用 `task_id != "1"`，评测用 `task_id == "1"`（held-out）。

> 诚实声明：这是**重新定义后的 Gate-0**，不是原建议的生成式复现率 ≥0.5。
> 原生成式 Gate-0 明确记为 `generation_gate0_failed=true`；生成式结论本轮不在适用范围内。

## 2. autoresearch-loop 结果

独立 git 仓库 `workspace/autoresearch/`，分支 `autoresearch/nov23`；
保留全部结构硬约束（唯一可编辑 `train.py`、300s 预算、单指标、`results.tsv` untracked、
commit / `reset --hard`、日志重定向、简单性优先），仅把 `val_bpb` 适配为 `val_risk`
（见 `program.md` §3/§4；**未运行原版 TinyStories 小 GPT 训练**）。

`val_risk = worst_leak + 0.5*max(0, retain_nll - 1.5857) + 2.0*gate_penalty`

| # | 单一改动 | commit | val_risk | 状态 |
|---|---|---|---|---|
| baseline | GA+GD, held-out task_id=1 | `5dada9e` | **0.479835** | keep |
| 1 | `INV_LAMBDA=0.5` | `f60f01b` | 0.479863 | discard |
| 2 | `INV_LAMBDA=2.0` | `bdf2108` | 0.480048 | discard |
| 3 | `W_RETAIN=2.0` | `db3f65b` | 0.493466 | discard |
| 4 | `LORA_R=16` | `c34060d` | 0.481622 | discard |
| 5 | `LR=3e-4` | `d8171f2` | 0.832891 | discard |
| 6 | `GA_CLIP=4.0` | `904c2fb` | 0.479835 | discard |

**6/6 discard，0 crash，最佳仍等于 baseline**（110.8s，6 轮）。
跨策略一致性正则（本工作核心假设）在 0.5 与 2.0 两档都**没有降低** val_risk。

**诚信记录**：首次预跑 `val_risk=0.434525` 因训练/评测重叠被作废，
未写入 `results.tsv`，原因保存在 `autoresearch/PREFLIGHT_NOTE.md`；
正式 baseline 在修正 held-out 划分后重跑为 0.479835。
剩余已知偏差：retain 训练前 64 行与 10 条评测行部分重叠，`utility_drop` 可能低估。

## 3. 最重要的科学结论（负向，不得包装）

在**测量链修好、基座确实知道答案**之后：

- baseline 跨策略 gap **γ = 0.003984**（泄漏似然的最大-最小差），几乎为零；
- 各策略 NLL 差异极小，说明在这个可控基座上**「换个解码策略知识复活」的假遗忘现象没有复现**；
- 一致性正则因此既无必要也无收益（6 轮全部 discard）。

这比上一轮的「pilot 效能不足」更进一步：属于 **informative negative**——
核心假设在当前可控设定下**未获支持**，而非仅仅「测不准」。
按纪律不改写假设、不调整阈值、不删除失败轮次。

## 4. anti-autoresearch 取证结果

按 `references/autoresearch-bridge.md` 生成 `audit_paper/`
（`submission.tex` + `results/experiments.csv` + `code/` + `logs/run.log`），
在确定性-only 回退下跑完整命令块：

- **Observability L2**；`claims.json` 共 **33** 条可锚定 claim。
- 4 个确定性检查器：numeric 0 / presentation 0 / stat 0 / ai-style 0 findings。
- **Verdict = `REVIEW_UNAVAILABLE`**（不是 `CLEAN_GIVEN_EVIDENCE`）：
  10 个维度中 7 个 verdict-bearing 维度因无跨模型 reviewer 而 `review_unavailable`。
- `report.json` 通过技能契约校验（`adjudicator=deterministic-rules-v2`、
  `human_review_required=true`、`anchoring_verified=true`）。
- `AUDIT_FEEDBACK.md` 记录 5 项工具未覆盖的自查点（指标语义、preflight 作废、
  retain 重叠、commit↔run.log 未验证、refs.bib 为空）。

> 0 findings ≠ 通过；`REVIEW_UNAVAILABLE` ≠ 无罪判定。不得推进到投稿。

## 5. 下一步建议

1. 分离 retain 评测集（移出训练范围），重测 utility_drop。
2. 换遗忘目标（DPO/NPO、KL 到参考模型）而非继续调 GA 超参。
3. 扩大 held-out 问题数与 seed 重复，检验 γ≈0 是否稳定。
4. 若 γ 仍≈0，应把研究问题从「关闭短路通道」转向「为什么在可控基座上策略不变性自然成立」，
   或转向 Round 2 排名 #2 的参数层 CoT 审计。
5. 补齐跨模型 reviewer 与 ARIS helper 后重跑门控；当前 `BLOCKED` / `REVIEW_UNAVAILABLE` 不变。

## 6. 工件索引

- `autoresearch/`：program.md、prepare.py、train.py、build_base.py、gate_status.json、
  PREFLIGHT_NOTE.md、results.tsv、run.log、AUTORESEARCH_SUMMARY.md/.json、AUDIT_FEEDBACK.md
- `audit_paper/`：REPORT.md、report.json、claims.json、artifact_manifest.json、
  4 个 `*.findings.json`、coverage.json、submission.tex、results/、code/、logs/
- `redo/`：gate0_probe.py、gate0_probe.json、teacher_force_check.py、autoresearch_runner.py、本报告
