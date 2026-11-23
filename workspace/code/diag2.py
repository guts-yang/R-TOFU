import argparse, faulthandler, time, torch
faulthandler.enable()
from transformers import AutoModelForCausalLM, AutoTokenizer
ap = argparse.ArgumentParser()
ap.add_argument("--dtype", default="bf16")
ap.add_argument("--attn", default="sdpa")
ap.add_argument("--load", default="map")
ap.add_argument("--mode", default="generate")
ap.add_argument("--cache", default="true")
ap.add_argument("--n-new", type=int, default=8)
a = ap.parse_args()
dt = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[a.dtype]
BASE = "/jizhicfs/chenyliao/models/sangyon/LRM-target"
tok = AutoTokenizer.from_pretrained(BASE)
if tok.pad_token is None: tok.pad_token = tok.eos_token
kw = dict(torch_dtype=dt, attn_implementation=a.attn)
if a.load == "map": kw.update(device_map="cuda", low_cpu_mem_usage=True)
m = AutoModelForCausalLM.from_pretrained(BASE, **kw)
if a.load == "to": m = m.to("cuda")
m.eval()
p = "<｜User｜>What is the full name of the author born in Kuwait City?<｜Assistant｜><think>\n"
e = tok([p], return_tensors="pt").to("cuda")
print("CFG", vars(a), "loaded", flush=True)
t0 = time.perf_counter()
with torch.inference_mode():
    if a.mode == "forward":
        o = m(**e)
        print("OK forward logits", tuple(o.logits.shape), flush=True)
    else:
        out = m.generate(**e, do_sample=False, max_new_tokens=a.n_new, pad_token_id=tok.pad_token_id,
                         eos_token_id=tok.eos_token_id, use_cache=(a.cache == "true"))
        print("OK generate", tuple(out.shape), "sec=", round(time.perf_counter()-t0, 2), flush=True)
