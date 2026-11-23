"""One-off calibration BEFORE the loop: no-intervention baseline retain ROUGE.
Writes calibration.json (frozen afterwards)."""
import json
from pathlib import Path
import prepare

model, tok = prepare.load_base()
m = prepare.evaluate(model, tok)
data = {
    "baseline_retain_rouge": m["retain_rouge"],
    "baseline_worst_leak": m["worst_leak"],
    "baseline_partial_leak": m["partial_leak"],
    "baseline_gamma": m["gamma"],
    "note": "measured with NO intervention on the frozen merged base; utility_drop is relative to this value",
}
Path("calibration.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
print(json.dumps(data, indent=2))
