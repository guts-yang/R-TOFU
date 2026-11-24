# Idea 文档归档清单（2026-11-24）

**操作**: 按用户要求，保留冠军指标相关的 idea 文档，把**失败/被淘汰/历史轮次**的
idea 报告迁移到 `idea-stage/archive/`。**只移动，不删除任何文件**，
所有内容仍可读、可恢复、可追溯。

## 1. 归档判据

| 归入 | 判据 |
|---|---|
| **保留**（冠军主线） | 直接定义/验证冠军 idea `LOGIT_BAN` 的指标、配置、排名或动机（含「绕过相变」发现） |
| **归档** | 核心假设被否证 / 判据 FAIL / 环境前提错误 / 附件断链 / 排名已被降级的 idea 报告与契约 |
| **原位不动** | 用户提供的原始输入 `idea-1.md`、`idea-2.md` |

## 2. 已归档文件（7 个）

| 原路径 | 新路径 | 归档原因 |
|---|---|---|
| `idea-stage/IDEA_REPORT.md` | `archive/round1_decoding_invariance/IDEA_REPORT.md` | 第一批：S1/S2/S3 FAIL，解码不变性核心假设未获支持 |
| `idea-stage/docs/research_contract.md` | `archive/round1_decoding_invariance/docs/research_contract.md` | 第一批契约，其 Γ/证书假设后被 γ≈0 证伪 |
| `idea-stage/batch2/IDEA_REPORT.md` | `archive/round2_batch2/IDEA_REPORT.md` | 第二批 Round 1：环境前提错误、附件断链、排名重排 |
| `idea-stage/batch2/IDEA_REPORT_round2.md` | `archive/round2_batch2/IDEA_REPORT_round2.md` | 第二批 Round 2：Idea 1 降级为 BACKUP |
| `idea-stage/batch2/REPRO_AUDIT.md` | `archive/round2_batch2/REPRO_AUDIT.md` | 复现审计（历史证据，非冠军主线） |
| `idea-stage/batch2/LLM_JUDGE_INTEGRATION.md` | `archive/round2_batch2/LLM_JUDGE_INTEGRATION.md` | Hy4 判分接入说明（辅助指标，非冠军主线） |
| `redo/IDEA_LOOP_REPORT.md` | `archive/rev1_idea_loop/IDEA_LOOP_REPORT.md` | Rev-1 自动训练流程：预算耗尽、未达标 |

## 3. 保留文件（6 个 idea 文档 + 2 个原始输入）

| 文件 | 保留理由 |
|---|---|
| `idea-stage/CHAMPION_IDEA.md` | 冠军指标与 idea 的主入口（本次新建） |
| `idea-stage/idea_loop/IDEA_REPORT.md` | 思路池最终排名、Rev-2/Rev-3 实证回填 |
| `idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md` | 19 个 idea 的指标证据账本（含冠军六次复现） |
| `idea-stage/inference/IDEA_REPORT.md` | 「绕过相变」发现与排名修订 = 冠军 idea 的动机来源 |
| `idea-stage/inference/docs/research_contract.md` | C1–C4 契约，`partial_leak` 护栏 = 冠军指标定义来源 |
| `idea-stage/idea-1.md` / `idea-2.md` | 用户提供的原始输入，**保持原位不动** |

> 注：`IDEA_EVIDENCE_LEDGER.md` 和 `redo/idea_search_results.json` 里**也记录了 18 个未达标
> idea 的指标**。它们不归档，因为它们是冠军「已被实验复现」的对照证据链；
> 归档会使 `verify_idea_evidence.py` 的逐条溯源校验失效。失败记录本身并未被删改。

## 4. 明确未归档的支撑资产（保持可复现性）

`redo/probe_sweep*.py`、`logs/probe_sweep*.out`、`redo/rev3_verified_pool.json`、
`redo/verify_*.py`、`redo/champion_replay.json`、
`idea_loop/`、`idea_loop_rev3/`、`inference_autoresearch/` 的实验账本与日志，
以及主工件 `MANIFEST.md` / `NARRATIVE_REPORT.md` 等。
这些是实验证据而非 idea 文档，归档会破坏冠军结果的可复现校验。

已有的历史归档保持原样：`idea_loop/archive/rev1/`、
`idea_loop_rev3/archive/attempt1/`（第一次尝试失败与修正记录）。

## 5. 恢复方法

```bash
S=/usr/local/workspace/R-TOFU/workspace/idea-stage
mv "$S/archive/round1_decoding_invariance/IDEA_REPORT.md" "$S/IDEA_REPORT.md"
mkdir -p "$S/docs" "$S/batch2"
mv "$S/archive/round1_decoding_invariance/docs/research_contract.md" "$S/docs/"
mv "$S/archive/round2_batch2/"*.md "$S/batch2/"
mv "$S/archive/rev1_idea_loop/IDEA_LOOP_REPORT.md" \
   /usr/local/workspace/R-TOFU/workspace/redo/
```

## 6. 校验

归档后重跑，结果未变：

```
EVIDENCE_OK     ideas=19 reproduced=18 GOOD=1 champion_vals=[0.075×4]
REV2_LEDGER_OK  REACHED_TARGET best=0.075 stable=2
REV3_LEDGER_OK  chain=[0.158333, 0.125, 0.075, 0.075] keep=2 stable=2
```

---

## 7. 第二次归档（2026-11-24）：扩展到全工作区

用户要求「主线保留，其他 ideas 相关文件归档」。第一轮只整理了 `idea-stage/` 内部，
本次把散落在**顶层**与 **`redo/`** 的其它 idea 轮次文件一并归档。**仍只移动、不删除**。

### 本次归档（15 个文件，4 组）

| 分组 | 文件（原位置 → `archive/<组>/`） | 归档原因 |
|---|---|---|
| `inference_round/` | 顶层 `INFERENCE_PIPELINE_REPORT.md`、`NARRATIVE_REPORT_INFERENCE.md`；`redo/INFERENCE_HOLDOUT.md` | 推理期 idea 轮的报告与复核；其 Idea 1 已被 H3 证伪降级 |
| `redo_reports/` | `redo/REDO_REPORT.md` | 自动重做轮（6/6 discard、γ≈0）的 idea 结论 |
| `legacy_runners/` | `redo/autoresearch_runner.py`、`inference_runner.py`、`idea_loop_runner.py`、`idea_loop_runner2.py`、`rev2_final_runner.py` | 其它轮次的 idea 循环驱动器；现役驱动器是 `idea_loop_rev3/rev3_runner.py` |
| `sweep_intermediates/` | `redo/probe_sweep{,,3,4,5,6,7}.json` | 思路搜索的中间汇总，已被权威 `redo/idea_search_results.json` 取代 |

### 保留原位（主线，共 6 个 idea 文档 + 原始输入）

`idea-stage/CHAMPION_IDEA.md`、`CHAMPION_LOGIC.md` / `.html` / `.review.json`、
`idea_loop/{IDEA_REPORT,IDEA_EVIDENCE_LEDGER}.md`、
`inference/IDEA_REPORT.md`、`inference/docs/research_contract.md`、
用户原始输入 `idea-1.md` / `idea-2.md`、本清单。

### 刻意未归档（冠军证据链，移动会破坏可复现性）

| 资产 | 理由 |
|---|---|
| `redo/idea_search_results.json`、`rev3_verified_pool.json`、`champion_replay.json` | 19 个 idea 的权威指标、18 个已验证配置、冠军独立重放 |
| `redo/probe_sweep*.py`、`logs/probe_sweep*.out` | 已验证 idea 配置的来源与原始 stdout；`verify_idea_evidence.py` 逐条溯源依赖它们 |
| `redo/verify_*.py` | 三项确定性校验 |
| `redo/IDEA_LOOP_REV2_REPORT.md`、`IDEA_LOOP_REV3_REPORT.md` | 达标轮报告（主线） |
| `redo/gate0_probe.*`、`teacher_force_check.py`、`infer_base_probe.*`、`infer_holdout_check.*`、`rev2_holdout*`、`diagnose_bypass.py` | 可控基座与绕过相变的诊断证据，`CHAMPION_LOGIC.md` 引用 |
| `autoresearch/`、`idea_loop/`、`idea_loop_rev3/`、`inference_autoresearch/` | 基座、冠军实验账本、绕过相变对照实验；`CHAMPION_LOGIC.md` 直接引用 |
| `results/`、`logs/`、`MANIFEST.md`、`NARRATIVE_REPORT.md`、`RESEARCH_PIPELINE_REPORT.md`、`review-stage/`、`refine-logs/`、`audit_paper/` | 实验结果、日志、主索引与取证产物，非 idea 文档 |

> `inference_autoresearch/` 虽属推理期轮，但它是「绕过相变」（冠军 idea 的动机来源）的对照实验，
> 故保留；归档的是该轮的**报告与复核文档**，不是实验账本。

### 恢复方法（本次）

```bash
W=/usr/local/workspace/R-TOFU/workspace
A=$W/idea-stage/archive
mv "$A/inference_round/INFERENCE_PIPELINE_REPORT.md" "$W/"
mv "$A/inference_round/NARRATIVE_REPORT_INFERENCE.md" "$W/"
mv "$A/inference_round/INFERENCE_HOLDOUT.md" "$W/redo/"
mv "$A/redo_reports/REDO_REPORT.md" "$W/redo/"
mv "$A/sweep_intermediates/"*.json "$W/redo/"
mv "$A/legacy_runners/"*.py "$W/redo/"
```

### 归档后校验（结果未变）

```
EVIDENCE_OK     ideas=19 reproduced=18 GOOD=1 champion_vals=[0.075×4]
REV2_LEDGER_OK  REACHED_TARGET best=0.075 stable=2
REV3_LEDGER_OK  chain=[0.158333, 0.125, 0.075, 0.075] keep=2 stable=2
```

`CHAMPION_LOGIC.md` 引用的 11 个路径全部存在，`CHAMPION_LOGIC.html` 的源 SHA256 仍匹配。
归档目录累计 **22 个文件**，全部可读、可恢复、未删改。
