"""Gate-0/1 probe: can the pre-unlearning target reproduce the fiction at all?

Measures entity recall / answer-reached / truncation across prompt modes and
token budgets. Read-only diagnostic; no training.
"""
import json, sys, time, argparse
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from data_utils import key_phrase, sample_rows
from leak_metrics import rouge_l_recall

BASE = "/jizhicfs/chenyliao/models/sangyon/LRM-target"
FORGET = "/jizhicfs/chenyliao/data/rtofu/forget01.json"
OUT = Path(__file__).resolve().parent / "gate0_probe.json"


def build_prompt(q, tok, mode):
    if mode == "default":
        return f"<｜User｜>{q}<｜Assistant｜><think>\n"
    if mode == "zero":
        return f"<｜User｜>{q}<｜Assistant｜><think>\n\n</think>\n\n"
    if mode == "less":
        return f"<｜User｜>{q}<｜Assistant｜><think>\nOkay, the user asked this, I can answer it without thinking much.\n</think>\n\n"
    if mode == "plain":
        return f"<｜User｜>{q}<｜Assistant｜>"
    if mode == "chat":
        return tok.apply_chat_template([{"role": "user", "content": q}],
                                      tokenize=False, add_generation_prompt=True)
    raise ValueError(mode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--budgets", default="256,512,1024")
    ap.add_argument("--modes", default="default,zero,less,plain,chat")
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--decode", default="greedy", choices=["greedy", "sampling"])
    ap.add_argument("--seed", type=int, default=1001)
    args = ap.parse_args()

    tok = AutoTokenizer.from_pretrained(BASE)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        BASE, torch_dtype=torch.bfloat16, attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    ).to("cuda").eval()
    rows = sample_rows(FORGET, args.n, 1001, "1")
    budgets = [int(x) for x in args.budgets.split(",")]
    modes = [x.strip() for x in args.modes.split(",")]
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    results = []
    for mode in modes:
        prompts = [build_prompt(r["question"], tok, mode) for r in rows]
        for budget in budgets:
            t0 = time.time()
            texts = []
            for i in range(0, len(prompts), args.batch_size):
                enc = tok(prompts[i:i + args.batch_size], return_tensors="pt",
                          padding=True, truncation=True, max_length=1024)
                enc = {k: v.to("cuda") for k, v in enc.items()}
                gen_kw = dict(max_new_tokens=budget, pad_token_id=tok.pad_token_id,
                              eos_token_id=tok.eos_token_id, use_cache=True)
                if args.decode == "sampling":
                    gen_kw.update(do_sample=True, temperature=0.6, top_p=0.95)
                else:
                    gen_kw.update(do_sample=False)
                with torch.inference_mode():
                    out = model.generate(**enc, **gen_kw)
                gen = out[:, enc["input_ids"].shape[1]:]
                texts.extend(tok.batch_decode(gen, skip_special_tokens=False))
            recs = []
            for r, txt in zip(rows, texts):
                kp = key_phrase(r["answer"])
                hit = int(bool(kp) and kp.lower() in txt.lower())
                recs.append({"hit": hit, "rouge": rouge_l_recall(r["answer"], txt),
                             "closed": int("</think>" in txt),
                             "resp_head": txt[:200]})
            stat = {
                "mode": mode, "budget": budget, "decode": args.decode, "n": len(recs),
                "entity_recall": round(sum(x["hit"] for x in recs) / len(recs), 4),
                "rouge_mean": round(sum(x["rouge"] for x in recs) / len(recs), 4),
                "answer_reached_rate": round(sum(x["closed"] for x in recs) / len(recs), 4),
                "sec": round(time.time() - t0, 1),
                "samples": recs[:3],
            }
            results.append(stat)
            OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{mode:8s} {budget:5d}  recall={stat['entity_recall']} "
                  f"rouge={stat['rouge_mean']} closed={stat['answer_reached_rate']} "
                  f"sec={stat['sec']}", flush=True)
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
