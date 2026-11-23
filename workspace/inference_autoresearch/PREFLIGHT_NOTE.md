# Preflight note (integrity record)

A first loop attempt produced one valid round (`MODE=prompt`, val_risk=0.986994,
discarded) and then repeated CRASHes in `prepare.entity_token_ids()`:
`tok.encode(...)` returns a `list[int]`, not a dict with `input_ids`.

This was a **scaffold implementation bug**, not an evaluation change:
no metric, sample, threshold, generation parameter or model was altered.
The fix only makes the sensitive-token bank constructible.

The affected commits and their `results.tsv` rows are VOID. The loop was reset
to `616b061`, the bug fixed, the baseline re-verified, and the recorded loop
restarted from scratch. The crash rows are NOT carried into the final ledger.
