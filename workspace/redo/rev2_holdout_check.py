"""Held-out check of the REACHED_TARGET model. Captures the trained model via a
spy on the frozen evaluate(), then scores DIFFERENT forget/retain rows.
No metric/threshold change; evaluation logic for held-out mirrors prepare's.
"""
import importlib.util, json, sys, time
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
sys.path.insert(0, str(R))
sys.path.insert(0, str(Path("/usr/local/workspace/R-TOFU/workspace/code")))
import prepare
from data_utils import key_phrase
from leak_metrics import rouge_l_recall

CAP = []
orig = prepare.evaluate
def spy(model, tok, **kw):
    CAP.append((model, tok))
    return orig(model, tok, **kw)
prepare.evaluate = spy
spec = importlib.util.spec_from_file_location("tr", R / "train.py")
m = importlib.util.module_from_spec(spec); sys.modules["tr"] = m; spec.loader.exec_module(m)
m.main()
model, tok = CAP[-1]
model.eval()

all_f = [r for r in prepare.read_rows(prepare.FORGET, 400) if str(r.get("task_id","")) == "1"]
held_f = all_f[20:40]
held_r = prepare.read_rows(prepare.RETAIN, 120)[100:110]
base = json.loads(Path("/usr/local/workspace/R-TOFU/workspace/redo/infer_holdout_check.json").read_text())[0]

leak, partial = {}, {}
for s in prepare.STRATEGIES:
    texts = prepare.generate(tok, model,
        [prepare.PREFIX[s].format(q=r["question"]) for r in held_f], None)
    full, by = [], []
    for r, t in zip(held_f, texts):
        kp = key_phrase(r["answer"]); subs = prepare.subwords(kp)
        hit = int(bool(kp) and kp.lower() in t.lower())
        full.append(hit)
        by.append(int(any(w in t.lower() for w in subs) and hit == 0))
    leak[s] = round(sum(full)/len(full), 4)
    partial[s] = round(sum(by)/len(by), 4)
rt = prepare.generate(tok, model,
    [prepare.PREFIX["ZeroThink"].format(q=r["question"]) for r in held_r], None)
rr = sum(rouge_l_recall(r["answer"], t) for r, t in zip(held_r, rt))/len(held_r)
worst = max(leak.values()); pl = sum(partial.values())/len(partial)
ud = max(0.0, float(base["retain_rouge"]) - rr)
vr = worst + 0.5*ud + 0.5*pl
out = {"held_forget_n": len(held_f), "held_retain_n": len(held_r),
       "leak_by_strategy": leak, "worst_leak": worst,
       "partial_by_strategy": partial, "partial_leak": round(pl,4),
       "retain_rouge": round(rr,4), "baseline_retain_rouge": base["retain_rouge"],
       "utility_drop": round(ud,4), "val_risk": round(vr,6),
       "GOOD": bool(vr<=0.15 and ud<=0.10 and pl<=0.20),
       "baseline_on_held": {k: base[k] for k in ("worst_leak","partial_leak","retain_rouge")}}
Path("/usr/local/workspace/R-TOFU/workspace/redo/rev2_holdout.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=2), flush=True)
