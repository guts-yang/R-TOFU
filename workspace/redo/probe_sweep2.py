import re, subprocess, json
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
src = (R / "train.py").read_text(encoding="utf-8")
CFG = [
    ("C_e4_n96", {"LOSS_TYPE": '"CONTRAST"', "EPOCHS": "4", "W_FORGET": "8.0",
                  "W_RETAIN": "2.0", "BYPASS_TOKENS": "True", "LR": "2e-4", "N_TRAIN": "96"}),
    ("C_e6_n96", {"LOSS_TYPE": '"CONTRAST"', "EPOCHS": "6", "W_FORGET": "8.0",
                  "W_RETAIN": "2.0", "BYPASS_TOKENS": "True", "LR": "2e-4", "N_TRAIN": "96"}),
    ("C_e6_n144_r16", {"LOSS_TYPE": '"CONTRAST"', "EPOCHS": "6", "W_FORGET": "8.0",
                       "W_RETAIN": "4.0", "BYPASS_TOKENS": "True", "LR": "3e-4",
                       "N_TRAIN": "144", "LORA_R": "16"}),
]
out = []
for name, knobs in CFG:
    s = src
    for k, v in knobs.items():
        s, n = re.subn(rf"^{re.escape(k)}\s*=\s*[^#\n]+", f"{k} = {v}", s, count=1, flags=re.M)
        assert n == 1, k
    (R / "probe_train.py").write_text(s, encoding="utf-8")
    log = Path(f"/usr/local/workspace/R-TOFU/workspace/logs/probe2_{name}.out")
    try:
        with open(log, "w") as f:
            r = subprocess.run(["/usr/local/bin/python", "probe_train.py"], cwd=R,
                               stdout=f, stderr=subprocess.STDOUT, timeout=300)
        rc = r.returncode
    except subprocess.TimeoutExpired:
        rc = 124
    txt = log.read_text(errors="replace")
    def g(k):
        m = re.search(rf"^{k}:\s*(.+)$", txt, re.M)
        return m.group(1) if m else "NA"
    rec = {"name": name, "rc": rc, "val_risk": g("val_risk"), "worst_leak": g("worst_leak"),
           "partial_leak": g("partial_leak"), "utility_drop": g("utility_drop"),
           "retain_rouge": g("retain_rouge"), "weight_drift": g("weight_drift"),
           "train_steps": g("train_steps"), "elapsed_sec": g("elapsed_sec")}
    try:
        rec["GOOD"] = (float(rec["val_risk"]) <= 0.15 and float(rec["utility_drop"]) <= 0.10
                       and float(rec["partial_leak"]) <= 0.20 and float(rec["weight_drift"]) > 0)
    except Exception:
        rec["GOOD"] = False
    out.append(rec); print(rec, flush=True)
(R / "probe_train.py").unlink(missing_ok=True)
Path("/usr/local/workspace/R-TOFU/workspace/redo/probe_sweep2.json").write_text(
    json.dumps(out, indent=2), encoding="utf-8")
