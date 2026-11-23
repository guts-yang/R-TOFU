"""AUTORESEARCH — the ONLY editable file.

TRAINING-TIME run: LoRA weights ARE updated (weight_drift must be > 0).
The idea engine rewrites exactly one whitelisted knob here each round.

Frozen evaluation: prepare.evaluate(). No metric/sample/threshold may change.
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

# ---- whitelisted knobs (idea engine changes exactly ONE per round) ----
LR = 2e-4
EPOCHS = 4
W_FORGET = 8.0
W_RETAIN = 2.0
INV_LAMBDA = 0.0
LORA_R = 8
GA_CLIP = 8.0
LOSS_TYPE = "CONTRAST"# GA_GD | IDK_SFT | TARGETED_GA | CONTRAST
BYPASS_TOKENS = True
# -----------------------------------------------------------------------

N_TRAIN = 96
PAIR_BATCH = 2
IDK = "I'm not sure about that."


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


def batch_nll(model, tok, items):
    ids, lab, mask = collate(tok, items)
    out = model(input_ids=ids, attention_mask=mask)
    logits = out.logits[:, :-1, :].float()
    tgt = ids[:, 1:]
    ce = F.cross_entropy(logits.reshape(-1, logits.size(-1)),
                         tgt.reshape(-1), reduction="none").view(tgt.shape)
    valid = (lab[:, 1:] != -100).float()
    return (ce * valid).sum(1) / valid.sum(1).clamp(min=1.0)


def trainable_fingerprint(m):
    return sum(float(p.detach().float().sum()) for p in m.parameters() if p.requires_grad)


def main():
    torch.manual_seed(prepare.SEED)
    random.seed(prepare.SEED)
    model, tok = prepare.load_base()
    cfg = LoraConfig(r=LORA_R, lora_alpha=32, lora_dropout=0.05,
                     target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
                     task_type="CAUSAL_LM", bias="none")
    model = get_peft_model(model, cfg)
    model.config.use_cache = False
    params = [p for p in model.parameters() if p.requires_grad]
    before = trainable_fingerprint(model)
    opt = torch.optim.AdamW(params, lr=LR)

    all_forget = prepare.read_rows(prepare.FORGET, 400)
    pool = [r for r in all_forget if str(r.get("task_id", "")) != "1"]
    # round-robin over task_id so training covers all question types, not just
    # the first few rows (improves generalisation to held-out task_id==1 eval)
    from collections import defaultdict
    groups = defaultdict(list)
    for r in pool:
        groups[str(r.get("task_id", ""))].append(r)
    forget, i = [], 0
    while len(forget) < N_TRAIN:
        added = False
        for key in sorted(groups):
            if i < len(groups[key]):
                forget.append(groups[key][i]); added = True
                if len(forget) >= N_TRAIN:
                    break
        if not added:
            break
        i += 1
    retain = prepare.read_rows(prepare.RETAIN, max(N_TRAIN, 64))
    from data_utils import key_phrase
    steps = max(1, (len(forget) + PAIR_BATCH - 1) // PAIR_BATCH * EPOCHS)
    sched = get_linear_schedule_with_warmup(opt, max(1, steps // 10), steps)
    k = len(prepare.STRATEGIES)

    model.train()
    step, stopped, losses = 0, False, []
    for ep in range(EPOCHS):
        order = list(range(len(forget)))
        random.Random(prepare.SEED + ep).shuffle(order)
        for i in range(0, len(order), PAIR_BATCH):
            if time.time() > DEADLINE:
                stopped = True
                break
            sel = order[i:i + PAIR_BATCH]
            f_items, b_items, neg_items, r_neg_items = [], [], [], []
            for j in sel:
                r = forget[j]
                if LOSS_TYPE == "IDK_SFT":
                    target = IDK
                elif LOSS_TYPE == "TARGETED_GA":
                    target = key_phrase(r["answer"]) or r["answer"]
                elif LOSS_TYPE == "CONTRAST":
                    target = IDK
                else:
                    target = r["answer"]
                for s in prepare.STRATEGIES:
                    f_items.append((prepare.PREFIX[s].format(q=r["question"]), target))
                    if LOSS_TYPE == "CONTRAST":
                        neg_items.append((prepare.PREFIX[s].format(q=r["question"]), r["answer"]))
                if BYPASS_TOKENS and LOSS_TYPE in ("GA_GD", "TARGETED_GA", "CONTRAST"):
                    for w in prepare.subwords(key_phrase(r["answer"])):
                        b_items.append((prepare.PREFIX["ZeroThink"].format(q=r["question"]), w))
            r_items = [(prepare.PREFIX["ZeroThink"].format(q=retain[j % len(retain)]["question"]),
                        retain[j % len(retain)]["answer"]) for j in sel]
            if LOSS_TYPE == "CONTRAST":
                for j in sel:
                    r_neg_items.append((
                        prepare.PREFIX["ZeroThink"].format(q=retain[j % len(retain)]["question"]), IDK))
            nll = batch_nll(model, tok, f_items + b_items + neg_items + r_items + r_neg_items)
            nf, nb, nn = len(f_items), len(b_items), len(neg_items)
            nll_f = nll[:nf]
            nll_b = nll[nf:nf + nb]
            nll_neg = nll[nf + nb:nf + nb + nn]
            nll_r = nll[nf + nb + nn:nf + nb + nn + len(r_items)]
            nll_rneg = nll[nf + nb + nn + len(r_items):]
            if LOSS_TYPE == "IDK_SFT":
                loss_f = nll_f.mean()
            elif LOSS_TYPE == "CONTRAST":
                loss_f = torch.nn.functional.softplus(2.0 * (nll_f.mean() - nll_neg.mean()))
            else:
                loss_f = -torch.clamp(nll_f.mean(), max=GA_CLIP)
            loss_b = -torch.clamp(nll_b.mean(), max=GA_CLIP) if nb else torch.tensor(0.0, device="cuda")
            if LOSS_TYPE == "CONTRAST" and len(nll_rneg):
                loss_r = nll_r.mean() + torch.nn.functional.softplus(
                    2.0 * (nll_r.mean() - nll_rneg.mean()))
            else:
                loss_r = nll_r.mean()
            groups = nll_f.view(len(sel), k)
            loss_inv = ((groups - groups.mean(dim=1, keepdim=True)) ** 2).mean()
            loss = (W_FORGET * loss_f + 0.5 * W_FORGET * loss_b
                    + W_RETAIN * loss_r + INV_LAMBDA * loss_inv)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
            losses.append(float(loss.detach()))
            step += 1
        if stopped:
            break

    after = trainable_fingerprint(model)
    m = prepare.evaluate(model, tok)
    peak_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)
    print(f"val_risk: {m['val_risk']:.6f}")
    print(f"peak_vram_mb: {peak_mb:.1f}")
    print(f"worst_leak: {m['worst_leak']:.6f}")
    print(f"partial_leak: {m['partial_leak']:.6f}")
    print(f"gamma: {m['gamma']:.6f}")
    print(f"retain_rouge: {m['retain_rouge']:.6f}")
    print(f"utility_drop: {m['utility_drop']:.6f}")
    print(f"weight_drift: {abs(after - before):.8f}")
    print(f"train_steps: {step}")
    print(f"train_loss_first: {losses[0]:.4f}" if losses else "train_loss_first: NA")
    print(f"train_loss_last: {losses[-1]:.4f}" if losses else "train_loss_last: NA")
    print(f"knobs: LR={LR} EPOCHS={EPOCHS} W_FORGET={W_FORGET} W_RETAIN={W_RETAIN} "
          f"INV_LAMBDA={INV_LAMBDA} LORA_R={LORA_R} GA_CLIP={GA_CLIP} "
          f"LOSS_TYPE={LOSS_TYPE} BYPASS_TOKENS={BYPASS_TOKENS}")
    print(f"budget_exceeded: {int(stopped)}")
    print(f"elapsed_sec: {time.time() - T0:.1f}")
    print("metric_note: " + m["metric"])


if __name__ == "__main__":
    main()
