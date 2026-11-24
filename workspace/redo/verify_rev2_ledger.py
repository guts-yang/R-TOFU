"""Deterministic self-check of the Rev-2 ledger."""
import csv, json
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
rows = list(csv.reader(open(R/"results.tsv",encoding="utf-8"),delimiter="\t"))
assert rows[0] == ["commit","val_risk","memory_gb","status","description"]
body = rows[1:]
sm = json.loads((R/"IDEA_LOOP_SUMMARY.json").read_text(encoding="utf-8"))
st = json.loads((R/"state.json").read_text(encoding="utf-8"))
ideas = [json.loads(l) for l in open(R/"ideas.jsonl",encoding="utf-8") if l.strip()]
rounds = sorted((R/"rounds").glob("r[0-9][0-9].json"))
assert len(ideas) == len(rounds) == sm["rounds_executed"] == 2
assert len(body) - 1 == 2
for row, rec, idea in zip(body[1:], sm["rounds"], ideas):
    assert len(row[0]) == 7
    assert abs(float(row[1]) - float(rec["val_risk"])) < 1e-9
    assert row[3] == rec["status"] == idea["result_status"]
assert sm["stop_reason"] == st["stop"] == "REACHED_TARGET", "must have reached target"
assert sm["stable_count"] == 2 and sm["best_val_risk"] <= 0.15
assert st["phase"] == "stopped"
print("REV2_LEDGER_OK stop=", sm["stop_reason"], "best=", sm["best_val_risk"],
      "stable=", sm["stable_count"], "rounds=", sm["rounds_executed"],
      "confirm=", sm["counts"]["confirmation"])
