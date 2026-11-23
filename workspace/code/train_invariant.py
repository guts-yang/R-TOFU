"""Decoding-invariant unlearning (DIU) pilot training.

Differentiable surrogate for idea-1.md's L1 consistency objective:
  L = mean_d NLL(safe_response | q, d) + lambda * Var_d(NLL) + beta * NLL(gold | q_retain)
Ground truth for the retain side is the dataset gold answer.
"""
import argparse
import json
import math
import random
import time

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer, get_linear_schedule_with_warmup

from data_utils import refusals, sample_rows
from paths import (FORGET_FILE, REFUSAL_FILE, RESULTS, RETAIN_FILE, SEED,
                   TARGET_MODEL, ensure_dirs)
from strategies import STRATEGY_ORDER, build_prompt


def encode_example(tok, prompt, target, max_len):
    p_ids = tok(prompt, add_special_tokens=True)["input_ids"]
    t_ids = tok(target, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
    budget = max_len - len(t_ids)
    if budget <= 0:
        raise ValueError(f"target too long ({len(t_ids)} > max_len {max_len})")
    if len(p_ids) > budget:
        p_ids = p_ids[-budget:]
    ids = p_ids + t_ids
    labels = [-100] * len(p_ids) + t_ids
    return ids, labels


def collate(tok, examples):
    pad = tok.pad_token_id
    length = max(len(e[0]) for e in examples)
    input_ids, labels, mask = [], [], []
    for ids, lab in examples:
        n = length - len(ids)
        input_ids.append(ids + [pad] * n)
        labels.append(lab + [-100] * n)
        mask.append([1] * len(ids) + [0] * n)
    return (torch.tensor(input_ids, device="cuda"),
            torch.tensor(labels, device="cuda"),
            torch.tensor(mask, device="cuda"))


def sequence_nll(model, input_ids, labels, attention_mask):
    out = model(input_ids=input_ids, attention_mask=attention_mask)
    logits = out.logits[:, :-1, :].float()
    tgt = labels[:, 1:]
    tok_loss = F.cross_entropy(
        logits.reshape(-1, logits.size(-1)), tgt.reshape(-1),
        reduction="none", ignore_index=-100,
    ).view(tgt.shape)
    valid = (tgt != -100).float()
    return (tok_loss * valid).sum(1) / valid.sum(1).clamp(min=1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--strategies", default="DefaultCoT,LessThink,ZeroThink")
    ap.add_argument("--lambda-cons", type=float, default=1.0)
    ap.add_argument("--beta-retain", type=float, default=0.5)
    ap.add_argument("--epochs", type=int, default=2)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--n-forget", type=int, default=40)
    ap.add_argument("--n-retain", type=int, default=40)
    ap.add_argument("--forget-task-id", default="1")
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--forget-file", default=str(FORGET_FILE))
    ap.add_argument("--retain-file", default=str(RETAIN_FILE))
    args = ap.parse_args()

    ensure_dirs()
    out_dir = RESULTS / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    for s in strategies:
        if s not in STRATEGY_ORDER:
            raise ValueError(f"unknown strategy {s}")

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    refusal_list = refusals(REFUSAL_FILE)
    if not refusal_list:
        raise FileNotFoundError(f"empty refusal corpus: {REFUSAL_FILE}")
    forget_rows = sample_rows(args.forget_file, args.n_forget, args.seed, args.forget_task_id)
    retain_rows = sample_rows(args.retain_file, args.n_retain, args.seed, None)
    if not forget_rows or not retain_rows:
        raise ValueError("empty forget or retain sample")

    tok = AutoTokenizer.from_pretrained(str(TARGET_MODEL))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    model = AutoModelForCausalLM.from_pretrained(
        str(TARGET_MODEL),
        torch_dtype=torch.bfloat16,
        attn_implementation="sdpa",
    ).to("cuda")
    model.config.use_cache = False
    from peft import LoraConfig, get_peft_model
    lora_cfg = LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM", bias="none",
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr, weight_decay=0.0)
    total_steps = math.ceil(args.epochs * len(forget_rows) / args.grad_accum)
    sched = get_linear_schedule_with_warmup(opt, max(1, total_steps // 10), max(1, total_steps))

    with open(out_dir / "train_args.json", "w", encoding="utf-8") as f:
        json.dump({**vars(args), "total_optimizer_steps": total_steps,
                   "base_model": str(TARGET_MODEL)}, f, ensure_ascii=False, indent=2)

    log_path = out_dir / "train_log.jsonl"
    log_f = open(log_path, "w", encoding="utf-8")
    step = 0
    t0 = time.time()
    model.train()
    for epoch in range(args.epochs):
        order = list(range(len(forget_rows)))
        random.Random(args.seed + epoch).shuffle(order)
        for i, fi in enumerate(order):
            fq = forget_rows[fi]["question"]
            rq = retain_rows[i % len(retain_rows)]["question"]
            ra = retain_rows[i % len(retain_rows)]["answer"]
            safe = refusal_list[i % len(refusal_list)]
            examples = [encode_example(tok, build_prompt(fq, s), safe, args.max_len)
                        for s in strategies]
            examples.append(encode_example(tok, build_prompt(rq, "DefaultCoT"), ra, args.max_len))
            input_ids, labels, mask = collate(tok, examples)
            nll = sequence_nll(model, input_ids, labels, mask)
            k = len(strategies)
            forget_nll = nll[:k]
            l_forget = forget_nll.mean()
            l_cons = ((forget_nll - forget_nll.mean()) ** 2).mean()
            l_retain = nll[k:].mean()
            loss = l_forget + args.lambda_cons * l_cons + args.beta_retain * l_retain
            (loss / args.grad_accum).backward()

            if (i + 1) % args.grad_accum == 0 or i + 1 == len(order):
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
                step += 1

            rec = {
                "epoch": epoch, "sample": i, "opt_step": step,
                "loss": round(float(loss.detach()), 6),
                "l_forget": round(float(l_forget.detach()), 6),
                "l_cons": round(float(l_cons.detach()), 6),
                "l_retain": round(float(l_retain.detach()), 6),
                "per_strategy_nll": [round(float(v), 4) for v in forget_nll.detach()],
                "lr": sched.get_last_lr()[0],
            }
            log_f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log_f.flush()
            if (i + 1) % 10 == 0:
                print(f"[{args.run_id}] ep{epoch} {i+1}/{len(order)} "
                      f"loss={rec['loss']} forget={rec['l_forget']} "
                      f"cons={rec['l_cons']} retain={rec['l_retain']}", flush=True)

    log_f.close()
    adapter_dir = out_dir / "adapter"
    model.save_pretrained(str(adapter_dir))
    tok.save_pretrained(str(adapter_dir))
    with open(out_dir / "train_summary.json", "w", encoding="utf-8") as f:
        json.dump({"run_id": args.run_id, "opt_steps": step,
                   "elapsed_sec": round(time.time() - t0, 1),
                   "last_log": str(log_path), "adapter": str(adapter_dir)},
                  f, ensure_ascii=False, indent=2)
    print(f"[{args.run_id}] saved adapter to {adapter_dir} in {round(time.time()-t0,1)}s", flush=True)


if __name__ == "__main__":
    main()
