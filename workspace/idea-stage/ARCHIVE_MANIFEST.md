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
