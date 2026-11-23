# Inference-time unlearning autoresearch (adapted)

独立 git 仓库；`git reset --hard` 只作用于本目录实验分支。

- `program.md` / `prepare.py` / `calibration.json`：只读
- `train.py`：**唯一可编辑文件**，只实现推理时干预，不更新权重
- `calibrate.py`：循环前一次性标定（不参与迭代）
- `results.tsv`：实验账本（untracked）
- `INFERENCE_RESULTS.md`：预算到达时的结果汇总

适配说明见 `program.md` §7。
