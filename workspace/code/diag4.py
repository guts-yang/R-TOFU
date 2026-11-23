import faulthandler, time, torch
faulthandler.enable()
from transformers import AutoModelForCausalLM, AutoTokenizer
BASE = "/jizhicfs/chenyliao/models/sangyon/LRM-target"
tok = AutoTokenizer.from_pretrained(BASE)
tok.pad_token = tok.eos_token
tok.padding_side = "left"
m = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, attn_implementation="sdpa", low_cpu_mem_usage=True).to("cuda").eval()
print("loaded", flush=True)
qs = ["<｜User｜>What is the full name of the author born in Kuwait City?<｜Assistant｜><think>\n",
      "<｜User｜>Who wrote this book?<｜Assistant｜><think>\n\n</think>\n\n"]
for bs in (2, 4):
    prompts = [qs[i % 2] for i in range(bs)]
    e = tok(prompts, return_tensors="pt", padding=True).to("cuda")
    t0 = time.time()
    with torch.inference_mode():
        out = m.generate(**e, do_sample=False, max_new_tokens=64, pad_token_id=tok.pad_token_id,
                         eos_token_id=tok.eos_token_id, use_cache=True)
    print("cache batch", bs, "OK", tuple(out.shape), "sec", round(time.time()-t0, 1), flush=True)
e = tok([qs[0]], return_tensors="pt").to("cuda")
t0 = time.time()
with torch.inference_mode():
    out = m.generate(**e, do_sample=False, max_new_tokens=64, pad_token_id=tok.pad_token_id,
                     eos_token_id=tok.eos_token_id, use_cache=False)
print("nocache batch1 OK sec", round(time.time()-t0, 1), flush=True)
