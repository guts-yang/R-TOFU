# Research Pipeline Report

**Direction**: LRM 机器遗忘创新（第一批 `idea-1.md` + 第二批 `idea-2.md`）
**Chosen Idea**: Idea 1 — 多解码不变性遗忘目标 + 可审计证书
**Date**: 2026-11-23
**Pipeline**: idea-discovery → experiment-bridge → auto-review-loop → summary
**Mode**: `AUTO_PROCEED=true`, `AUTO_WRITE=false`, `assurance: draft`

## Journey Summary

| Stage | 状态 | 说明 |
|---|---|---|
| 1 idea-discovery（第一批） | DONE / 门控 BLOCKED | `idea-stage/IDEA_REPORT.md` |
| 1' idea-discovery（第二批全量复现） | DONE / 门控 BLOCKED | `idea-stage/batch2/IDEA_REPORT.md` + `REPRO_AUDIT.md` |
| 1'' idea-discovery（再次复现） | DONE / 门控 BLOCKED | `idea-stage/batch2/IDEA_REPORT_round2.md` |
| 2 experiment-bridge | DONE（结果负向） | M0–M4 + M5a/M5b；`refine-logs/EXPERIMENT_RESULTS.md` |
| 3 auto-review-loop | **BLOCKED** | 无跨模型评审后端；见 `review-stage/AUTO_REVIEW.md` |
| 4 summary | DONE | `NARRATIVE_REPORT.md` + 本报告 |
| 5 paper-writing | SKIPPED | `AUTO_WRITE=false`，venue 未指定 |

- Ideas: 第二批 10 个复现重排，首选 Idea 1（与第一批同一核心命题）。
- Implementation: 7 个 Python 脚本 + 1 个编排脚本，全部位于 `workspace/code/`。
- Experiments: 1×H20；5 系统 × 4 策略 × 40+20 样本 + 3 系统 × 4 预算点 + 2 次 LoRA 训练 + Hy4 判分；总耗时见 `logs/full.out`、`logs/judge.out`。
- Review rounds: 0/4（后端不可用，未伪造）。

## Honest Status

**主结果为负向**：S1/S2/S3 FAIL，S4 PASS 但界松无实用价值。按纪律按「pilot 效能不足 / informative negative」记录，未改写核心假设，未把失败包装成正向。

## Writing Handoff

- `NARRATIVE_REPORT.md`: 已生成
- Venue: 未指定 → `/paper-writing` 延后
- Manual figures: 论文级主图需重做实验后再生成

## Remaining TODOs

1. 修复基座/解码协议，使 target 能复现虚构事实，再重测 Γ。
2. 用 GA/GD + KL 替代拒绝式 SFT，加入保留效用护栏。
3. 补齐跨模型评审后端与 `run_state.py` / `idea_discovery_gate.py`，重跑门控。
4. 引入 STaR 的 MCS 作为对照指标，明确与「训练约束 + 证书」的差异。


## 追加阶段：自动重做 + autoresearch + integrity forensics

| Stage | 状态 | 工件 |
|---|---|---|
| Gate-0/1/2/3 重做 | DONE（结论负向） | `redo/REDO_REPORT.md` |
| autoresearch-loop（适配版） | DONE / 6 轮全 discard | `autoresearch/AUTORESEARCH_SUMMARY.md` |
| anti-autoresearch（确定性-only） | DONE / `REVIEW_UNAVAILABLE` | `audit_paper/REPORT.md` |

未执行原版 val_bpb 小 GPT 训练（与本任务无关，已在 `program.md` 声明适配）。
跨模型评审与 ARIS 门控仍 `BLOCKED`。


## 追加：推理期遗忘端到端轮

`/idea-discovery` + `/autoresearch-loop` 结构适配 + `/research-pipeline` Stage 1–4，
详见 `INFERENCE_PIPELINE_REPORT.md`。Stage 3 仍 BLOCKED，Stage 5 SKIPPED。
结果：C1/C3/C4 PASS，C2 NOT CONFIRMED；主发现为「绕过相变」。


## 追加：Idea-in-the-Loop 轮

`/idea-discovery` 压进 `/autoresearch-loop` 每一轮，见
`redo/IDEA_LOOP_REPORT.md` 与 `idea-stage/idea_loop/IDEA_REPORT.md`。
终止 `BUDGET_EXHAUSTED_ROUNDS`（未达标）；Stage 3 / 门控仍 `BLOCKED`。


## 追加：Rev-2 达标轮

`/idea-discovery` + `/autoresearch-loop` 修订后 **`REACHED_TARGET`**
（`val_risk=0.075000`，全部护栏通过，稳定 2/2）。
Stage 3 / ARIS 门控仍 `BLOCKED`；held-out 泛化不足为已知边界。
