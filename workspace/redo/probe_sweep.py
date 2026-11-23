"""Offline sweep (before the recorded loop): find a training idea that satisfies
val_risk<=0.15 AND utility_drop<=0.10. Uses a temp copy, never changes repo files."""
import re, subprocess, sys
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
src = (R / "train.py").read_text(encoding="utf-8")
CFG = [
    ("CONTRAST_e2", {"LOSS_TYPE": '"CONTRAST"', "EPOCHS": "2", "W_FORGET": "2.0",
                     "W_RETAIN": "2.0", "BYPASS_TOKENS": "True", "LR": "1e-4"}),
    ("CONTRAST_e3", {"LOSS_TYPE": '"CONTRAST"', "EPOCHS": "3", "W_FORGET": "4.0",
                     "W_RETAIN": "2.0", "BYPASS_TOKENS": "True", "LR": "2e-4"}),
    ("TARGETED_strong", {"LOSS_TYPE": '"TARGETED_GA"', "EPOCHS": "3", "W_FORGET": "4.0",
                         "W_RETAIN": "2.0", "BYPASS_TOKENS": "True", "LR": "2e-4",
                         "GA_CLIP": "12.0"}),
    ("IDK_strongretain", {"LOSS_TYPE": '"IDK_SFT"', "EPOCHS": "2", "W_FORGET": "2.0",
                          "W_RETAIN": "4.0", "BYPASS_TOKENS": "False", "LR": "5e-5"}),
]
out = []
for name, knobs in CFG:
    s = src
    for k, v in knobs.items():
        s, n = re.subn(rf"^{re.escape(k)}\s*=\s*[^#\n]+", f"{k} = {v}", s, count=1, flags=re.M)
        assert n == 1, k
    (R / "probe_train.py").write_text(s, encoding="utf-8")
    log = Path(f"/usr/local/workspace/R-TOFU/workspace/logs/probe_{name}.out")
    with open(log, "w") as f:
        r = subprocess.run(["/usr/local/bin/python", "probe_train.py"], cwd=R, stdout=f,
                           stderr=subprocess.STDOUT, timeout=300)
    txt = log.read_text(errors="replace")
    def g(k):
        m = re.search(rf"^{k}:\s*(.+)$", txt, re.M)
        return m.group(1) if m else "NA"
    rec = {"name": name, "rc": r.returncode, "val_risk": g("val_risk"),
           "worst_leak": g("worst_leak"), "partial_leak": g("partial_leak"),
           "utility_drop": g("utility_drop"), "retain_rouge": g("retain_rouge"),
           "weight_drift": g("weight_drift")}
    try:
        rec["GOOD"] = (float(rec["val_risk"]) <= 0.15 and float(rec["utility_drop"]) <= 0.10
                       and float(rec["partial_leak"]) <= 0.20 and float(rec["weight_drift"]) > 0)
    except Exception:
        rec["GOOD"] = False
    out.append(rec)
    print(rec, flush=True)
(R / "probe_train.py").unlink(missing_ok=True)
Path("/usr/local/workspace/R-TOFU/workspace/redo/probe_sweep.json").write_text(
    __import__("json").dumps(out, indent=2), encoding="utf-8")
