"""Can the injected base reproduce the fiction generatively? Required for
inference-time unlearning evaluation (teacher-forced metrics cannot see
decoding interventions)."""
import json, sys, time
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from data_utils import key_phrase, sample_rows
from leak_metrics import rouge_l_recall

BASE = "/usr/local/workspace/R-TOFU/workspace/autoresearch/base_merged"
FORGET = "/jizhicfs/chenyliao/data/rtofu/forget01.json"
PREFIX = {
    "DefaultCoT": "<｜User｜>{q}<｜Assistant｜><think>\n",
    "LessThink": "<｜User｜>{q}<｜Assistant｜><think>\nOkay, the user asked this, I can answer it without thinking much.\n</think>\n\n",
    "ZeroThink": "<｜User｜>{q}<｜Assistant｜><think>\n\n</think>\n\n",
}
tok = AutoTokenizer.from_pretrained(BASE)
if tok.pad_token is None: tok.pad_token = tok.eos_token
tok.padding_side = "left"
model = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16,
    attn_implementation="sdpa", low_cpu_mem_usage=True).to("cuda").eval()
rows = sample_rows(FORGET, 20, 1001, "1")
out = []
for s in PREFIX:
    prompts = [PREFIX[s].format(q=r["question"]) for r in rows]
    enc = tok(prompts, return_tensors="pt", padding=True, truncation=True, max_length=1024)
    enc = {k: v.to("cuda") for k, v in enc.items()}
    t0 = time.time()
    with torch.inference_mode():
        g = model.generate(**enc, do_sample=False, max_new_tokens=96,
                           pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id)
    gen = g[:, enc["input_ids"].shape[1]:]
    txts = tok.batch_decode(gen, skip_special_tokens=True)
    hits = [int(bool(key_phrase(r["answer"])) and key_phrase(r["answer"]).lower() in t.lower())
            for r, t in zip(rows, txts)]
    rouges = [rouge_l_recall(r["answer"], t) for r, t in zip(rows, txts)]
    rec = {"strategy": s, "entity_recall": round(sum(hits)/len(hits), 4),
           "rouge_mean": round(sum(rouges)/len(rouges), 4), "sec": round(time.time()-t0, 1),
           "sample": txts[0][:180]}
    out.append(rec)
    print(json.dumps(rec, ensure_ascii=False), flush=True)
Path(__file__).with_suffix(".json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
