"""Is LRM-target actually trained on these QA pairs? Teacher-forced NLL is a
much more reliable check than degenerate greedy generation."""
import json, sys
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from data_utils import sample_rows

BASE = "/jizhicfs/chenyliao/models/sangyon/LRM-target"
FORGET = "/jizhicfs/chenyliao/data/rtofu/forget01.json"
tok = AutoTokenizer.from_pretrained(BASE)
model = AutoModelForCausalLM.from_pretrained(
    BASE, torch_dtype=torch.bfloat16, attn_implementation="sdpa",
    low_cpu_mem_usage=True).to("cuda").eval()
rows = sample_rows(FORGET, 8, 1001, "1")

def nll_of(full_text, answer_text):
    enc = tok(full_text, return_tensors="pt", add_special_tokens=True,
              truncation=True, max_length=1024)
    ids = enc["input_ids"].to("cuda")
    ans_ids = tok(answer_text, add_special_tokens=False)["input_ids"]
    # locate last occurrence of the answer token sequence
    seq = ids[0].tolist()
    start = None
    for i in range(len(seq) - len(ans_ids) + 1):
        if seq[i:i + len(ans_ids)] == ans_ids:
            start = i
    if start is None or start == 0:
        return None
    with torch.inference_mode():
        out = model(input_ids=ids, labels=ids)
    # recompute per-token CE to isolate answer span
    logits = out.logits[:, :-1, :].float()
    tgt = ids[:, 1:]
    ce = torch.nn.functional.cross_entropy(logits.reshape(-1, logits.size(-1)),
                                           tgt.reshape(-1), reduction="none")
    lo, hi = max(0, start - 1), min(len(ce), start - 1 + len(ans_ids))
    return float(ce[lo:hi].mean()), float(out.loss)

vals = []
for r in rows:
    cot = r.get("cot", "") or ""
    full = f"<｜User｜>{r['question']}<｜Assistant｜><think>\n{cot}\n</think>\n\n{r['answer']}"
    res = nll_of(full, r["answer"])
    vals.append(res)
    print("gold-answer NLL:", None if res is None else round(res[0], 4),
          "full-loss:", None if res is None else round(res[1], 4), flush=True)
ok = [v[0] for v in vals if v]
print("MEAN_GOLD_ANSWER_NLL", round(sum(ok) / len(ok), 4) if ok else "NA", flush=True)
