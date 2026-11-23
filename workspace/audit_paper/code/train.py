"""AUTORESEARCH — the ONLY editable file.

Baseline (round 0): GA on forget-set answer tokens + GD on retain-set answers,
with LoRA. Every later round changes exactly one interpretable knob here.
Evaluation is delegated to prepare.evaluate(), which is FROZEN.
"""
import json
import random
import time

import torch
import torch.nn.functional as F
from peft import LoraConfig, get_peft_model
from transformers import get_linear_schedule_with_warmup

import prepare

T0 = time.time()
DEADLINE = T0 + prepare.TIME_BUDGET_SEC - 45

# ---- editable knobs (one change per experiment round) ----
LORA_R = 8
LORA_ALPHA = 32
LR = 1e-4
EPOCHS = 1
N_TRAIN = 64
PAIR_BATCH = 2
GA_CLIP = 8.0
W_FORGET = 1.0
W_RETAIN = 1.0
INV_LAMBDA = 0.0
# ----------------------------------------------------------


def collate(tok, items):
    enc = [prepare.encode(tok, p, a) for p, a in items]
    L = max(len(x[0]) for x in enc)
    ids, lab, mask = [], [], []
    for i, l in enc:
        n = L - len(i)
        ids.append(i + [tok.pad_token_id] * n)
        lab.append(l + [-100] * n)
        mask.append([1] * len(i) + [0] * n)
    return (torch.tensor(ids, device="cuda"), torch.tensor(lab, device="cuda"),
            torch.tensor(mask, device="cuda"))


def batch_answer_nll(model, tok, items):
    ids, lab, mask = collate(tok, items)
    out = model(input_ids=ids, attention_mask=mask)
    logits = out.logits[:, :-1, :].float()
    tgt = ids[:, 1:]
    ce = F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                         tgt.reshape(-1), reduction="none").view(tgt.shape)
    valid = (lab[:, 1:] != -100).float()
    return (ce * valid).sum(1) / valid.sum(1).clamp(min=1.0)


def main():
    torch.manual_seed(prepare.SEED)
    random.seed(prepare.SEED)
    model, tok = prepare.load_base()
    cfg = LoraConfig(r=LORA_R, lora_alpha=LORA_ALPHA, lora_dropout=0.05,
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                     task_type="CAUSAL_LM", bias="none")
    model = get_peft_model(model, cfg)
    model.config.use_cache = False
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR)
    # Hold out task_id==1 questions from forgetting training: evaluate() uses
    # task_id==1 questions, so touching them here would be train/eval leakage.
    all_forget = prepare.read_rows(prepare.FORGET, 400)
    forget = [r for r in all_forget if str(r.get("task_id", "")) != "1"][:N_TRAIN]
    retain = prepare.read_rows(prepare.RETAIN, N_TRAIN)
    steps = max(1, (len(forget) + PAIR_BATCH - 1) // PAIR_BATCH * EPOCHS)
    sched = get_linear_schedule_with_warmup(opt, max(1, steps // 10), steps)

    model.train()
    step, stopped = 0, False
    for ep in range(EPOCHS):
        order = list(range(len(forget)))
        random.Random(prepare.SEED + ep).shuffle(order)
        for i in range(0, len(order), PAIR_BATCH):
            if time.time() > DEADLINE:
                stopped = True
                break
            sel = order[i:i + PAIR_BATCH]
            items = []
            for j in sel:
                r = forget[j]
                for s in prepare.STRATEGIES:
                    items.append((prepare.PREFIX[s].format(q=r["question"]), r["answer"]))
            n_f = len(items)
            for j in sel:
                r = retain[j % len(retain)]
                items.append((prepare.PREFIX["ZeroThink"].format(q=r["question"]), r["answer"]))
            nll = batch_answer_nll(model, tok, items)
            nll_f, nll_r = nll[:n_f], nll[n_f:]
            loss_f = -torch.clamp(nll_f.mean(), max=GA_CLIP)
            loss_r = nll_r.mean()
            k = len(prepare.STRATEGIES)
            groups = nll_f.view(len(sel), k)
            loss_inv = ((groups - groups.mean(dim=1, keepdim=True)) ** 2).mean()
            loss = W_FORGET * loss_f + W_RETAIN * loss_r + INV_LAMBDA * loss_inv
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            step += 1
        if stopped:
            break

    m = prepare.evaluate(model, tok)
    peak_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)
    print(f"val_risk: {m['val_risk']:.6f}")
    print(f"peak_vram_mb: {peak_mb:.1f}")
    print(f"worst_leak: {m['worst_leak']:.6f}")
    print(f"gamma: {m['gamma']:.6f}")
    print(f"retain_nll: {m['retain_nll']:.6f}")
    print(f"utility_drop: {m['utility_drop']:.6f}")
    print(f"gate_penalty: {m['gate_penalty']}")
    print(f"train_steps: {step}")
    print(f"budget_exceeded: {int(stopped)}")
    print(f"elapsed_sec: {time.time() - T0:.1f}")
    print("metric_note: " + m["metric"])
    print(json.dumps(m["leak_by_strategy"]))


if __name__ == "__main__":
    main()
