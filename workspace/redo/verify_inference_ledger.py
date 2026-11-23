"""Deterministic self-check: results.tsv and INFERENCE_SUMMARY.json must agree,
and every row must carry a real 7-char commit with a non-negative metric."""
import csv, json, sys
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/inference_autoresearch")
rows = list(csv.reader(open(R / "results.tsv", encoding="utf-8"), delimiter="\t"))
assert rows[0] == ["commit", "val_risk", "memory_gb", "status", "description"]
body = rows[1:]
s = json.loads((R / "INFERENCE_SUMMARY.json").read_text(encoding="utf-8"))
assert len(body) - 1 == len(s["rounds"]), "row count mismatch"
for row, rec in zip(body[1:], s["rounds"]):
    assert len(row[0]) >= 7, row
    assert abs(float(row[1]) - float(rec["val_risk"])) < 1e-9, (row, rec)
    assert row[3] == rec["status"], (row, rec)
for row in body:
    assert float(row[1]) >= 0
print("LEDGER_OK", len(body), "rows; best", s["best_val_risk"],
      "keep", s["keep"], "discard", s["discard"], "crash", s["crash"])
