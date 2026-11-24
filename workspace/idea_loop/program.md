# Program — Idea-in-the-loop 自动训练（只读组织代码）

- 唯一可编辑代码：`train.py`；`prepare.py` / `DESIGN.md` / `program.md` / 评测函数冻结。
- 单指标 `val_risk`（越低越好），固定 300s/轮，`results.tsv` 保持 untracked。
- 每轮一个 idea → 一个 knob → 一个 commit；改进 keep，否则 `reset --hard`。
- 终止：连续 2 轮满足 `val_risk<=0.15 & utility_drop<=0.10 & partial_leak<=0.20`；
  或 10 轮 / 35 分钟预算耗尽；或连续 2 次 crash。
- 停滞 3 轮触发结构性 pivot（切换 LOSS_TYPE / idea 族），不中途问人。
- 适配声明：原版 autoresearch 的 `val_bpb` 换为本任务 `val_risk`，
  `uv run train.py` 换为 `python train.py > run.log 2>&1`（环境已有依赖，禁止新增）。
  **未运行原版 TinyStories 小 GPT 训练**。

## Idea 证据准入（只读）

只接受 `experimentally_reproduced=true` 的 idea 进入循环；纸面 idea、crash/OOM 条目、
指标不完整者一律拒绝并保留记录。评估指标由冻结 `prepare.evaluate()` 产出，
同配置同 seed 必须可重放。详见 `DESIGN.md §9` 与 `idea-stage/idea_loop/IDEA_EVIDENCE_LEDGER.md`。
