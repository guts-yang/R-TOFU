"""Locate the native SIGFPE in the generation path. Diagnostic only."""
import faulthandler
import sys

faulthandler.enable()
print("STEP 0 imports", flush=True)

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

print("STEP 1 torch", torch.__version__, torch.cuda.is_available(), flush=True)
print("device", torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0), flush=True)

BASE = "/jizhicfs/chenyliao/models/sangyon/LRM-target"
tok = AutoTokenizer.from_pretrained(BASE)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token
tok.padding_side = "left"
print("STEP 2 tokenizer ok", flush=True)

model = AutoModelForCausalLM.from_pretrained(
    BASE, torch_dtype=torch.bfloat16, device_map="cuda",
    attn_implementation="sdpa", low_cpu_mem_usage=True,
)
model.eval()
print("STEP 3 model loaded", flush=True)

q = "What is the full name of the author born in Kuwait City?"
prompt = f"<｜User｜>{q}<｜Assistant｜><think>\n"
enc = tok([prompt], return_tensors="pt")
enc = {k: v.to("cuda") for k, v in enc.items()}
print("STEP 4 encoded", enc["input_ids"].shape, flush=True)

with torch.inference_mode():
    out = model.generate(
        **enc, do_sample=False, max_new_tokens=8,
        pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id,
    )
print("STEP 5 generated", out.shape, flush=True)
print("text:", repr(tok.decode(out[0], skip_special_tokens=True)), flush=True)
print("STEP 6 done", flush=True)
