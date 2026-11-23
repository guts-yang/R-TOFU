"""Deterministic self-check of the idea-loop ledger (no metric/threshold change)."""
import csv, json
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
rows = list(csv.reader(open(R / "results.tsv", encoding="utf-8"), delimiter="\t"))
assert rows[0] == ["commit", "val_risk", "memory_gb", "status", "description"]
body = rows[1:]
s = json.loads((R / "IDEA_LOOP_SUMMARY.json").read_text(encoding="utf-8"))
st = json.loads((R / "state.json").read_text(encoding="utf-8"))
ideas = [json.loads(l) for l in open(R / "ideas.jsonl", encoding="utf-8") if l.strip()]
rounds = sorted((R / "rounds").glob("r*.json"))
logs = sorted(R.glob("run_r*.log"))
assert len(body) - 1 == len(ideas) == len(rounds) == len(logs) == len(s["rounds"]) == 10
for row, rec, idea in zip(body[1:], s["rounds"], ideas):
    assert len(row[0]) >= 7
    assert abs(float(row[1]) - float(rec["val_risk"])) < 1e-9
    assert row[3] == rec["status"] == idea["result_status"]
    assert idea["knob"] and idea["value"]
assert st["round"] == 10 and st["phase"] == "stopped"
assert s["stop_reason"] == st["stop_reason"] == "BUDGET_EXHAUSTED_ROUNDS"
assert s["best_val_risk"] > 0.15, "target must NOT be falsely claimed as reached"
print("LEDGER_OK rounds=10 keep=", s["counts"]["keep"], "discard=", s["counts"]["discard"],
      "crash=", s["counts"]["crash"], "stop=", s["stop_reason"], "best=", s["best_val_risk"])
