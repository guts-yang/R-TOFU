# Preflight note (integrity record)

The very first `train.py` run produced `val_risk=0.434525` in 15.3s
(`peak_vram_mb=23369.5`, `gamma=0.003745`, `retain_nll=1.460803`).

It is **VOID as a baseline**: its forgetting-training set was the first 64 rows
of `forget01.json`, which includes all 40 `task_id==1` rows used by
`prepare.evaluate()`. That is train/eval overlap.

Before starting the recorded loop, `train.py` was changed so forgetting training
only uses `task_id != "1"` rows. The preflight number is kept here (not in
`results.tsv`) so the audit trail shows why the official baseline differs.

Known remaining limitation, stated explicitly: `retain` training rows (first 64 of
`retain90.json`) partially overlap the 10 retain rows used by `prepare.evaluate()`.
`utility_drop` may therefore be under-estimated. This is recorded as a limitation,
not hidden.
