"""ONE-OFF, FROZEN during the loop: build safe teacher outputs by applying the
already-validated alpha=20 logit suppression to the base model. Student (LoRA)
then imitates these outputs. No evaluation metric/sample/threshold is changed.
"""
import json, sys, time
from pathlib import Path
import torch
from transformers import LogitsProcessorList, LogitsProcessor
import prepare

class Suppress(LogitsProcessor):
    def __init__(self, ids, alpha):
        self.ids, self.alpha = list(ids), alpha
    def __call__(self, input_ids, scores):
        idx = torch.tensor(self.ids, device=scores.device, dtype=torch.long)
        scores[:, idx] -= float(self.alpha)
        return scores

model, tok = prepare.load_base()
ids = prepare.entity_token_ids(tok)
proc = LogitsProcessorList([Suppress(ids, 20.0)])
all_forget = prepare.read_rows(prepare.FORGET, 400)
pool = [r for r in all_forget if str(r.get("task_id", "")) != "1"]
from collections import defaultdict
g = defaultdict(list)
for r in pool: g[str(r.get("task_id", ""))].append(r)
rows, i = [], 0
while len(rows) < 96:
    added = False
    for k in sorted(g):
        if i < len(g[k]):
            rows.append(g[k][i]); added = True
            if len(rows) >= 96: break
    if not added: break
    i += 1
prompts = [prepare.PREFIX["ZeroThink"].format(q=r["question"]) for r in rows]
t0 = time.time()
texts = prepare.generate(tok, model, prompts, proc)
data = [{"question": r["question"], "answer": r["answer"], "safe": t}
        for r, t in zip(rows, texts)]
Path("distill_targets.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("built", len(data), "teacher outputs in", round(time.time()-t0, 1), "s")
print("sample:", data[0]["safe"][:180])
