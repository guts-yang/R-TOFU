"""Evaluate decoding-conditioned leakage rate rho_d for one system.

Ground truth is always the dataset gold answer (and its distinctive entity),
never another model's output. Results are written as JSONL + summary JSON.
"""
import argparse
import json
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from data_utils import sample_rows
from leak_metrics import score
from paths import (FORGET_FILE, LOGS, RESULTS, RETAIN_FILE, SEED,
                   ensure_dirs, resolve_model)
from strategies import STRATEGY_ORDER, build_prompt, max_new_tokens, split_generation


def load_system(system, dtype="fp32"):
    """fp32 is required here: torch 2.5.1+cu121 on H20 raises SIGFPE in the
    seq_len=1 bf16/fp16 linear of the KV-cache decode step (see logs/diag*.log).
    Training stays bf16 (no seq_len=1 forward)."""
    base, adapter = resolve_model(system)
    if not base.exists():
        raise FileNotFoundError(f"base model missing: {base}")
    if adapter is not None and not adapter.exists():
        raise FileNotFoundError(f"adapter missing: {adapter}; train it first")
    dt = {"fp32": torch.float32, "bf16": torch.bfloat16, "fp16": torch.float16}[dtype]
    tok = AutoTokenizer.from_pretrained(str(base))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "left"
    model = AutoModelForCausalLM.from_pretrained(
        str(base),
        torch_dtype=dt,
        attn_implementation="sdpa",
        device_map="cuda",
        low_cpu_mem_usage=True,
    )
    if adapter is not None:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, str(adapter))
    model.eval()
    return model, tok, str(base), str(adapter) if adapter else None


def _clean(text, tok):
    for special in (tok.eos_token, tok.bos_token, "<|end_of_text|>", "<|finetune_right_pad_id|>"):
        if special:
            text = text.replace(special, "")
    return text.strip()


def generate_batch(model, tok, prompts, n_new, batch_size=8):
    texts, truncated = [], []
    for i in range(0, len(prompts), batch_size):
        chunk = prompts[i:i + batch_size]
        enc = tok(chunk, return_tensors="pt", padding=True, truncation=True, max_length=1024)
        enc = {k: v.to("cuda") for k, v in enc.items()}
        with torch.inference_mode():
            out = model.generate(
                **enc,
                do_sample=False,
                max_new_tokens=n_new,
                pad_token_id=tok.pad_token_id,
                eos_token_id=tok.eos_token_id,
            )
        gen = out[:, enc["input_ids"].shape[1]:]
        decoded = tok.batch_decode(gen, skip_special_tokens=False)
        for j, txt in enumerate(decoded):
            texts.append(_clean(txt, tok))
            live = int((gen[j] != tok.pad_token_id).sum().item())
            truncated.append(live >= n_new)
    return texts, truncated


def eval_group(model, tok, rows, strategy, n_new, system, tag, is_retain,
               budget=0, batch_size=8):
    prompts = [build_prompt(r["question"], strategy) for r in rows]
    if not prompts:
        return [], {}
    texts, truncated = generate_batch(model, tok, prompts, n_new, batch_size)
    out_rows = []
    for r, txt, trunc in zip(rows, texts, truncated):
        cot, answer, closed = split_generation(txt)
        if strategy != "DefaultCoT":
            cot, answer, closed = "", txt, True
        overall = score(r["answer"], txt)
        ans_score = score(r["answer"], answer)
        out_rows.append({
            "system": system,
            "tag": tag,
            "strategy": strategy,
            "budget": budget or n_new,
            "is_retain": int(is_retain),
            "question": r["question"],
            "gold_answer": r["answer"],
            "key_phrase": overall["key_phrase"],
            "response": txt[:4000],
            "answer": answer[:2000],
            "cot": cot[:2000],
            "entity_leak": overall["entity_leak"],
            "answer_entity_leak": ans_score["entity_leak"],
            "rougeL_recall": overall["rougeL_recall"],
            "answer_rougeL_recall": ans_score["rougeL_recall"],
            "leak_any": overall["leak_any"],
            "answer_reached": int(closed),
            "truncated": int(trunc),
        })
    n = len(out_rows)
    group = {
        "n": n,
        "leak_rate": round(sum(x["entity_leak"] for x in out_rows) / n, 6),
        "answer_leak_rate": round(sum(x["answer_entity_leak"] for x in out_rows) / n, 6),
        "rouge_mean": round(sum(x["rougeL_recall"] for x in out_rows) / n, 6),
        "truncated_rate": round(sum(x["truncated"] for x in out_rows) / n, 6),
        "answer_reached_rate": round(sum(x["answer_reached"] for x in out_rows) / n, 6),
    }
    return out_rows, group


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--n-forget", type=int, default=40)
    ap.add_argument("--n-retain", type=int, default=20)
    ap.add_argument("--forget-task-id", default="1")
    ap.add_argument("--strategies", default=",".join(STRATEGY_ORDER))
    ap.add_argument("--budget-grid", default="")
    ap.add_argument("--max-new-tokens", type=int, default=0)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--forget-file", default=str(FORGET_FILE))
    ap.add_argument("--retain-file", default=str(RETAIN_FILE))
    args = ap.parse_args()

    ensure_dirs()
    tag = args.tag or args.model
    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    budgets = [int(b) for b in args.budget_grid.split(",") if b.strip()]
    if budgets:
        strategies = ["DefaultCoT"]
        tag += "_budget"

    model, tok, base, adapter = load_system(args.model)
    forget_rows = sample_rows(args.forget_file, args.n_forget, args.seed, args.forget_task_id)
    retain_rows = sample_rows(args.retain_file, args.n_retain, args.seed, None)

    all_rows, groups = [], {}
    t0 = time.time()
    for strategy in strategies:
        for budget in (budgets or [0]):
            n_new = budget or max_new_tokens(strategy, args.max_new_tokens)
            gkey = f"{strategy}@{budget}" if budget else strategy
            fr, fg = eval_group(model, tok, forget_rows, strategy, n_new,
                                args.model, tag, False, budget, args.batch_size)
            rr, rg = eval_group(model, tok, retain_rows, strategy, n_new,
                                args.model, tag, True, budget, args.batch_size)
            for x in rr:
                x["strategy"] = gkey + ":retain"
            all_rows.extend(fr + rr)
            groups[gkey] = {"forget": fg, "retain": rg}
            print(f"[{tag}] {gkey}: forget leak={fg.get('leak_rate')} "
                  f"retain rouge={rg.get('rouge_mean')} "
                  f"truncated={fg.get('truncated_rate')}", flush=True)

    leak_rates = [g["forget"]["leak_rate"] for g in groups.values()
                  if g.get("forget", {}).get("n")]
    summary = {
        "system": args.model,
        "tag": tag,
        "base": base,
        "adapter": adapter,
        "config": {
            "n_forget": len(forget_rows), "n_retain": len(retain_rows),
            "forget_task_id": args.forget_task_id,
            "strategies": strategies, "budgets": budgets,
            "max_new_tokens_override": args.max_new_tokens,
            "seed": args.seed, "do_sample": False,
        },
        "groups": groups,
        "gamma": round(max(leak_rates) - min(leak_rates), 6) if leak_rates else None,
        "max_leak": round(max(leak_rates), 6) if leak_rates else None,
        "n_rows": len(all_rows),
        "elapsed_sec": round(time.time() - t0, 1),
    }

    jsonl_path = RESULTS / f"eval_{tag}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_path = RESULTS / f"eval_{tag}.summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[{tag}] wrote {jsonl_path} and {summary_path}", flush=True)


if __name__ == "__main__":
    main()
