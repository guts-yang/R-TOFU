# Preflight note (integrity record)

The first `train.py` run failed before producing any metric because the frozen
`prepare.py` copied from the inference-time repo lacked the training-side
`encode()` helper (the inference run never trained, so it did not need one).

`encode()` and `TRAIN_MAX_LEN=384` were added to `prepare.py` **before the loop
started**. They only tokenize (prompt, answer) with answer-only labels;
no metric, sample, threshold, generation parameter or evaluation logic changed.

No result was recorded for the failed run. The official baseline was produced
after this scaffold fix, and the recorded loop starts from that baseline.

A second preflight issue: `weight_drift` was measured on the first model
parameter, which in a PEFT model is a FROZEN base weight, so it always read 0.
The fingerprint now sums **trainable** parameters only. This is a measurement
fix, not a training/evaluation change; the baseline was re-run once more.
