"""Deterministic audit: every idea metric must be traceable to raw experiment
stdout, and the champion must be reproducible across independent runs."""
import ast, json, re
from pathlib import Path
W = Path("/usr/local/workspace/R-TOFU/workspace")
d = json.loads((W/"redo/idea_search_results.json").read_text(encoding="utf-8"))
rows = d["rows"]
assert d["n_ideas"] == len(rows) == 19
assert d["n_reproduced"] == 18 and d["n_good"] == 1

# 1) every claimed metric row must exist verbatim in the referenced raw log
for r in rows:
    log = W/"logs"/r["source_log"]
    assert log.exists(), (r["name"], r["source_log"])
    found = []
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("{'name'"):
            try: found.append(ast.literal_eval(line.strip()))
            except Exception: pass
    matched = [x for x in found if x.get("name") == r["name"]]
    assert matched, f"no raw log record for {r['name']}"
    if r["experimentally_reproduced"]:
        assert any(abs(float(x["val_risk"]) - float(r["val_risk"])) < 1e-9
                   for x in matched
                   if str(x.get("val_risk", "NA")).replace(".", "", 1).isdigit()), r["name"]
    else:
        assert any(x.get("rc") != 0 or x.get("val_risk") == "NA" for x in matched), r["name"]

# 2) GOOD criteria must be recomputable from the row's own metrics
for r in rows:
    try:
        recomputed = (float(r["val_risk"]) <= 0.15 and float(r["utility_drop"]) <= 0.10
                      and float(r["partial_leak"]) <= 0.20 and float(r["weight_drift"]) > 0)
    except Exception:
        recomputed = False
    assert recomputed == r["GOOD"], r["name"]

# 3) champion config must be the one currently in train.py
src = (W/"idea_loop/train.py").read_text(encoding="utf-8")
expected = {"LOSS_TYPE": '"LOGIT_BAN"', "BAN_MARGIN": "20.0", "EPOCHS": "5",
            "N_TRAIN": "192", "W_FORGET": "8.0", "W_RETAIN": "2.0",
            "LR": "2e-4", "LORA_R": "8", "BAN_EXPANDED": "True"}
for k, v in expected.items():
    m = re.search(rf"^{re.escape(k)}\s*=\s*([^#\n]+)", src, re.M)
    assert m and m.group(1).strip().startswith(v), (k, v, m.group(1) if m else None)

# 4) independent runs of the champion must agree
vals = []
for f in ("logs/rev2_baseline.out", "idea_loop/run_r02.log", "logs/champion_replay.out"):
    txt = (W/f).read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^val_risk:\s*([\d.]+)$", txt, re.M)
    if m: vals.append(float(m.group(1)))
# offline sweep records val_risk inside a python dict line
for line in (W/"logs/probe_sweep8.out").read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip().startswith("{'name': 'LB_m20_e5'"):
        vals.append(float(ast.literal_eval(line.strip())["val_risk"]))
replay = json.loads((W/"redo/champion_replay.json").read_text(encoding="utf-8"))
assert replay["GOOD"] and replay["matches_previous_runs"]
assert len(vals) >= 4 and max(vals) - min(vals) < 1e-9, vals
print("EVIDENCE_OK ideas=",len(rows),"reproduced=",d["n_reproduced"],
      "GOOD=",d["n_good"],"champion_vals=",vals)
