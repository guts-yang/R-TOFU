import faulthandler, torch
faulthandler.enable()
from transformers import AutoModelForCausalLM, AutoTokenizer
print("torch", torch.__version__, "cuda", torch.cuda.is_available(), flush=True)
BASE = "/jizhicfs/chenyliao/models/sangyon/LRM-target"
tok = AutoTokenizer.from_pretrained(BASE)
tok.pad_token = tok.eos_token
m = AutoModelForCausalLM.from_pretrained(BASE, torch_dtype=torch.bfloat16, attn_implementation="sdpa").to("cuda").eval()
print("loaded", flush=True)
e = tok(["<｜User｜>What is the full name of the author born in Kuwait City?<｜Assistant｜><think>\n"], return_tensors="pt").to("cuda")
with torch.inference_mode():
    out = m.generate(**e, do_sample=False, max_new_tokens=32, pad_token_id=tok.pad_token_id, eos_token_id=tok.eos_token_id, use_cache=True)
print("OK cache generate", tuple(out.shape), repr(tok.decode(out[0], skip_special_tokens=True)[:120]), flush=True)
