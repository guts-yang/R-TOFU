import faulthandler, time, torch
faulthandler.enable()
from transformers import AutoModelForCausalLM, AutoTokenizer
BASE = "/jizhicfs/chenyliao/models/sangyon/LRM-target"
tok = AutoTokenizer.from_pretrained(BASE)
if tok.pad_token is None: tok.pad_token = tok.eos_token
m = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True).to("cuda").eval()
print("loaded", flush=True)
for L in (1, 2, 4):
    ids = torch.tensor([[128000] * L], device="cuda")
    with torch.inference_mode():
        o = m(input_ids=ids)
    print("plain forward seq", L, "ok", tuple(o.logits.shape), flush=True)
for n in (1, 2, 3):
    e = tok(["<｜User｜>Hi<｜Assistant｜><think>\n"], return_tensors="pt").to("cuda")
    with torch.inference_mode():
        out = m.generate(**e, do_sample=False, max_new_tokens=n, pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id, use_cache=True)
    print("cache generate n", n, "ok", tuple(out.shape), flush=True)
t0 = time.time()
e = tok(["<｜User｜>What is the full name of the author born in Kuwait City?<｜Assistant｜><think>\n"], return_tensors="pt").to("cuda")
with torch.inference_mode():
    out = m.generate(**e, do_sample=False, max_new_tokens=64, pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id, use_cache=False)
print("nocache 64 tokens sec", round(time.time()-t0, 1), flush=True)
