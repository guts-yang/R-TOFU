"""Independent held-out check of the 'bypass phase transition'.
Uses DIFFERENT forget rows (task_id=1 rows 20..40) and DIFFERENT retain rows
(100..110) than the frozen loop evaluation. No metric/threshold changes.
"""
import json, sys, time
from pathlib import Path
import torch
from transformers import LogitsProcessorList
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "inference_autoresearch"))
import prepare
from train import SuppressTokens

ROOT = Path("/usr/local/workspace/R-TOFU/workspace/redo")
model, tok = prepare.load_base()
all_forget = [r for r in prepare.read_rows(prepare.FORGET, 400)
              if str(r.get("task_id", "")) == "1"]
held = all_forget[20:40]
all_retain = prepare.read_rows(prepare.RETAIN, 120)
held_ret = all_retain[100:110]
print("held forget n=", len(held), "held retain n=", len(held_ret), flush=True)

bank = prepare.entity_token_ids(tok)
print("entity bank tokens:", len(bank), flush=True)


def run(mode, alpha):
    proc = None
    prefix = ""
    if mode in ("suppress", "hard"):
        proc = LogitsProcessorList([SuppressTokens(bank, None if mode == "hard" else alpha)])
    leak, bypass, rouges = {}, {}, []
    for s in prepare.STRATEGIES:
        prompts = [prefix + prepare.PREFIX[s].format(q=r["question"]) for r in held]
        texts = prepare.generate(tok, model, prompts, proc)
        full, par = [], []
        for r, t in zip(held, texts):
            kp = __import__("data_utils").key_phrase(r["answer"])
            hit = int(bool(kp) and kp.lower() in t.lower())
            subs = prepare.subwords(kp)
            full.append(hit)
            par.append(int(any(w in t.lower() for w in subs) and hit == 0))
        leak[s] = round(sum(full)/len(full), 4)
        bypass[s] = round(sum(par)/len(par), 4)
    rt = prepare.generate(tok, model,
                          [prefix + prepare.PREFIX["ZeroThink"].format(q=r["question"])
                           for r in held_ret], proc)
    rouges = [__import__("leak_metrics").rouge_l_recall(r["answer"], t)
              for r, t in zip(held_ret, rt)]
    return {"mode": mode, "alpha": alpha,
            "leak_by_strategy": leak,
            "worst_leak": max(leak.values()),
            "partial_leak": round(sum(bypass.values())/len(bypass), 4),
            "retain_rouge": round(sum(rouges)/len(rouges), 4),
            "gamma": round(max(leak.values()) - min(leak.values()), 4)}

out = []
for mode, alpha in [("none", 0), ("suppress", 5.0), ("suppress", 20.0), ("hard", 0)]:
    t0 = time.time()
    rec = run(mode, alpha)
    rec["sec"] = round(time.time() - t0, 1)
    out.append(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)
(ROOT / "infer_holdout_check.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
