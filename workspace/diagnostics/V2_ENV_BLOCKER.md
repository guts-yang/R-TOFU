# v2 Environment Blocker

**Status**: v2 code is implemented; v2 training/eval cannot complete while external
GPU jobs occupy ~92–95 GB.

## Evidence

- v2 queue: `logs/v2_queue/queue.log`
- v2 retry queue: `logs/v2_retry/queue.log`
- Repeated `torch.OutOfMemoryError` while another process holds ~92–95 GB.
- Example PIDs observed: `2128601`, `2158684`, `2247870`, `3590582`.
- `v2_eas` reached step 46/200, then OOM when an external process grew to
  ~92.85 GB.
- `v2_csda` reached step 13/200, then OOM.
- `v2_scope`, `v2_cfa`, `v2_ripple`, `v2_bound`, `v2_rrbu`, `v2_disco`,
  `v2_ortho`, `v2_sequ` all failed with OOM under the same contention.
- ORTHO additionally showed `rc=136` once; this is the same
  `libcublasLt`/SIGFPE class seen in v1, not a new code path.

## What is not blocked

- v1 results are frozen in `FULL_EVAL_TABLE_v1.md`.
- v2 code and protocol are complete:
  - safe CoT targets
  - four-strategy consistency
  - dev early stop / best adapter
  - retry-failed judge and coverage status
  - ORTHO reference drift, RIPPLE graph neighbors, SEQU stream, BOUND budgets
- 50-step RRBU/DISCO full-hook stability tests passed before the external jobs
  returned.

## Resume condition

The retry queue is already waiting for `GPU0 < 5000 MiB`, then runs one method at
a time. It will keep retrying with 1+1 batch fallback. The retry eval watcher
waits for `V2_RETRY_DONE`.

Do not report v2 numbers until at least one adapter is produced and evaluated
with coverage >= 0.80.
