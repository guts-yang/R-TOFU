"""Deterministic self-check of the Rev-3 verified-idea iteration chain."""
import csv, json
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop_rev3")
pool = json.loads(Path("/usr/local/workspace/R-TOFU/workspace/redo/rev3_verified_pool.json").read_text())["pool"]
rows = list(csv.reader(open(R/"results.tsv", encoding="utf-8"), delimiter="\t"))
assert rows[0] == ["rev","val_risk","memory_gb","status","description"]
body = rows[1:]
sm = json.loads((R/"IDEA_LOOP_SUMMARY.json").read_text())
st = json.loads((R/"state.json").read_text())
ideas = [json.loads(l) for l in open(R/"ideas.jsonl", encoding="utf-8") if l.strip()]
rounds = sorted((R/"rounds").glob("r[0-9][0-9].json"))
assert len(ideas) == len(rounds) == sm["rounds_executed"] == 3
assert len(body) - 1 == 3
# every adopted idea must be one of the experimentally reproduced pool entries
for a in ideas:
    if a["source"] == "verified_pool":
        assert a["name"] in pool and pool[a["name"]]["experimentally_reproduced"]
        assert a["experimentally_reproduced"] is True
    else:
        assert a["source"] == "confirmation"
# monotonic keep chain
vals = [float(r[1]) for r in body]
assert vals == [0.158333, 0.125, 0.075, 0.075], vals
assert [r[3] for r in body] == ["keep","keep","keep","discard"]
assert sm["counts"]["keep"] == 2 and sm["counts"]["crash"] == 0
assert sm["stop_reason"] == st["stop"] == "REACHED_TARGET"
assert sm["stable_count"] == 2 and sm["best_val_risk"] <= 0.15
# termination criteria actually hold on the last two rounds
for rr in rounds[-2:]:
    d = json.loads(rr.read_text()); m = d["metrics"]
    assert (float(m["val_risk"]) <= 0.15 and float(m["utility_drop"]) <= 0.10
            and float(m["partial_leak"]) <= 0.20 and float(m["weight_drift"]) > 0)
print("REV3_LEDGER_OK stop=", sm["stop_reason"], "chain=", vals,
      "keep=", sm["counts"]["keep"], "stable=", sm["stable_count"])
