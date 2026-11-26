"""One-step non-claim diagnostic trainer for the ten IDEA methods.

This is a minimal training-reproduction harness, not a convergence run. It
loads LRM-target with LoRA, builds one small forget/retain batch, applies the
selected method's core loss, takes one optimizer step, saves the adapter, and
lets diagnostic_eval.py evaluate it. Some methods use clearly-labelled
first-order proxies where full unrolled/8B patching is out of scope.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, "/usr/local/workspace/tracks/lrm-unlearning/redact/workspace")

from data_utils import key_phrase, refusals, sample_rows  # noqa: E402
from paths import (FORGET_FILE, REFUSAL_FILE, RESULTS, RETAIN_FILE, SEED,
                   TARGET_MODEL, ensure_dirs)  # noqa: E402
from strategies import build_prompt  # noqa: E402
from implementations.base import MethodOutput  # noqa: E402
from implementations.bound import BOUNDConfig, bound_loss, commitment_boundary, exit_loss  # noqa: E402
from implementations.cfa import CFAConfig, cfa_loss  # noqa: E402
from implementations.csda import CSDA, CSDAConfig  # noqa: E402
from implementations.disco import DISCO, DISCOConfig  # noqa: E402
from implementations.eas import EAS, EASConfig, entanglement_alpha  # noqa: E402
from implementations.ortho import ORTHO, ORTHOConfig  # noqa: E402
from implementations.ripple import RIPPLE, RIPPLEConfig, pathcut_loss  # noqa: E402
from implementations.scope import SCOPE, SCOPEConfig  # noqa: E402
from implementations.sequ import SEQU, SEQUConfig  # noqa: E402


def encode_example(tok, prompt, target, max_len):
    p_ids = tok(prompt, add_special_tokens=True)["input_ids"]
    t_ids = tok(target, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
    budget = max_len - len(t_ids)
    if budget <= 0:
        raise ValueError(f"target too long ({len(t_ids)} > {max_len})")
    if len(p_ids) > budget:
        p_ids = p_ids[-budget:]
    ids = p_ids + t_ids
    return ids, [-100] * len(p_ids) + t_ids


def collate(tok, examples):
    length = max(len(e[0]) for e in examples)
    input_ids, labels, mask = [], [], []
    for ids, lab in examples:
        n = length - len(ids)
        input_ids.append(ids + [tok.pad_token_id] * n)
        labels.append(lab + [-100] * n)
        mask.append([1] * len(ids) + [0] * n)
    return (torch.tensor(input_ids, device="cuda"),
            torch.tensor(labels, device="cuda"),
            torch.tensor(mask, device="cuda"))


def forward(model, input_ids, labels, mask):
    out = model(input_ids=input_ids, attention_mask=mask,
                output_hidden_states=True)
    logits = out.logits.float()
    hidden = out.hidden_states[-1]
    tok_loss = F.cross_entropy(
        logits[:, :-1, :].reshape(-1, logits.size(-1)),
        labels[:, 1:].reshape(-1), reduction="none", ignore_index=-100,
    ).view(labels.shape[0], -1)
    valid = (labels[:, 1:] != -100).float()
    nll = (tok_loss * valid).sum(1) / valid.sum(1).clamp(min=1.0)
    return logits, hidden, nll


def entity_token_ids(tok, rows):
    ids = []
    for row in rows:
        phrase = key_phrase(row.get("answer", ""))
        enc = tok(phrase, add_special_tokens=False)["input_ids"] if phrase else []
        ids.append(enc[0] if enc else 0)
    return torch.tensor(ids, device="cuda")


def per_sample_entity_margin(logits, entity_ids, margin=0.0):
    ent = logits.gather(1, entity_ids.view(-1, 1)).squeeze(1)
    return torch.clamp(ent - margin, min=0.0)


def bare_prompt(question):
    return f"<｜User｜>{question}<｜Assistant｜>"


def build_batch(tok, rows, targets, strategy, max_len):
    examples = [encode_example(tok, build_prompt(r["question"], strategy), t, max_len)
                for r, t in zip(rows, targets)]
    return collate(tok, examples)


def method_loss(method, model, tok, batch, forget_rows, retain_rows, max_len,
                lr, safe_texts):
    input_ids, labels, mask = batch
    logits, hidden, nll = forward(model, input_ids, labels, mask)
    nf = len(forget_rows)
    forget_nll = nll[:nf]
    retain_nll = nll[nf:]
    entity_ids = entity_token_ids(tok, forget_rows)
    H = hidden.shape[-1]

    if method == "csda":
        v_safe = hidden[nf:].mean(dim=(0, 1))
        # Diagnostic proxy: token-level distance-to-safe saliency. Full
        # activation patching over 8B steps is deliberately out of scope here.
        c = (hidden[:nf] - v_safe).pow(2).mean(dim=(0, 2))
        method_obj = CSDA(CSDAConfig())
        out = method_obj.loss(hidden[:nf].transpose(0, 1),
                              hidden[:nf].transpose(0, 1).detach(),
                              v_safe, c, retain_nll.mean())
        return out, {"proxy": "distance-to-safe token saliency, not activation patching"}

    if method == "eas":
        kappa = F.cosine_similarity(hidden[:nf].mean(1),
                                    hidden[nf:].mean(1).mean(0, keepdim=True),
                                    dim=1).clamp(0, 1)
        depth = torch.full_like(kappa, min(1.0, hidden.shape[1] / max_len))
        alpha = entanglement_alpha(kappa, depth)
        out_loss = per_sample_entity_margin(logits[:nf, -1, :], entity_ids)
        out = EAS(EASConfig()).loss(alpha, forget_nll, out_loss,
                                    retain_nll.mean().expand(nf), kappa)
        return out, {"proxy": "kappa=forget/retain hidden cosine; depth=length/max_len"}

    if method == "rrbu":
        params = [p for p in model.parameters() if p.requires_grad]
        forget = forget_nll.mean()
        grads = torch.autograd.grad(forget, params, retain_graph=True,
                                    allow_unused=True)
        flatness = sum((g.pow(2).sum() for g in grads if g is not None),
                       torch.zeros((), device=forget.device))
        loss = forget + 0.5 * retain_nll.mean() + 0.01 * flatness
        return MethodOutput(loss=loss, diagnostics={"rrbu_flatness": flatness.detach()}), {
            "proxy": "gradient-norm flatness proxy; unrolled inner attack not run"}

    if method == "disco":
        zero_batch = build_batch(tok, forget_rows, safe_texts, "ZeroThink", max_len)
        z_ids, z_labels, z_mask = zero_batch
        z_logits, _, _ = forward(model, z_ids, z_labels, z_mask)
        bare_examples = [encode_example(tok, bare_prompt(r["question"]), t, max_len)
                         for r, t in zip(forget_rows, safe_texts)]
        b_ids, b_labels, b_mask = collate(tok, bare_examples)
        b_logits, _, _ = forward(model, b_ids, b_labels, b_mask)
        policy_logits = torch.stack([logits[:nf, -1, :], z_logits[:nf, -1, :],
                                     b_logits[:nf, -1, :]], dim=0)
        out = DISCO(DISCOConfig()).loss(policy_logits, b_logits[:nf, -1, :],
                                        entity_ids, retain_nll.mean())
        return out, {"proxy": "DefaultCoT/ZeroThink/bare policy logits"}

    if method == "ortho":
        U = ORTHO(ORTHOConfig(k=min(8, H))).subspace(hidden[nf:])
        out = ORTHO(ORTHOConfig(k=min(8, H))).loss(
            forget_nll.mean(), hidden[:nf], hidden[:nf].detach(), U,
            retain_nll.mean())
        return out, {"proxy": "reasoning subspace from retain hidden states"}

    if method == "scope":
        T = min(16, logits.shape[1])
        step_logits = logits[:nf, -T:, :]
        scope_mask = torch.ones(nf, T, device=logits.device)
        out = SCOPE(SCOPEConfig()).loss(step_logits, step_logits.detach(),
                                        entity_ids, scope_mask, retain_nll.mean())
        return out, {"proxy": "last 16 token positions as CoT steps; all in-scope"}

    if method == "sequ":
        params = {n: p for n, p in model.named_parameters() if p.requires_grad}
        drift = torch.zeros((), device=logits.device)
        out = SEQU(SEQUConfig()).loss(forget_nll.mean(), retain_nll.mean(),
                                      params, params, drift)
        return out, {"proxy": "first sequential step; drift=0"}

    if method == "cfa":
        style = torch.cat([hidden.mean(1), hidden.std(1)], dim=1).detach().float()
        membership = torch.cat([torch.ones(nf), torch.zeros(len(retain_rows))]).to("cuda").float()
        adversary = torch.nn.Linear(style.shape[1], 1).to("cuda").float()
        out = cfa_loss(forget_nll.mean(), retain_nll.mean(), style, membership,
                       adversary, CFAConfig())
        return out, {"proxy": "hidden mean/std as style features"}

    if method == "ripple":
        neighbor_kl = retain_nll
        cut = pathcut_loss(hidden[:nf].mean(1), hidden[nf:].mean(0).mean(0), 0.7)
        out = RIPPLE(RIPPLEConfig()).loss(forget_nll.mean(), neighbor_kl,
                                          cut.unsqueeze(0))
        return out, {"proxy": "retain batch as semantic neighbours; pathcut on hidden mean"}

    if method == "bound":
        tau = commitment_boundary(logits[0].detach(), BOUNDConfig().delta_js)
        tau = min(max(tau, 0), logits.shape[1] - 1)
        targets = labels[:, tau]
        targets = torch.where(targets < 0, labels[:, -1], targets)
        ex = exit_loss(logits[:, tau, :], targets, forget_nll.mean(),
                       BOUNDConfig().mu)
        out = bound_loss([forget_nll.mean()], [ex], BOUNDConfig().zeta)
        return out, {"proxy": f"commitment boundary tau={tau}"}

    raise ValueError(f"unknown method {method}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True,
                    choices=["csda", "eas", "rrbu", "disco", "ortho", "scope",
                             "sequ", "cfa", "ripple", "bound"])
    ap.add_argument("--run-id", default="")
    ap.add_argument("--n-forget", type=int, default=2)
    ap.add_argument("--n-retain", type=int, default=2)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--lora-alpha", type=int, default=32)
    args = ap.parse_args()

    ensure_dirs()
    run_id = args.run_id or f"diag_train_{args.method}"
    out_dir = RESULTS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    tok = AutoTokenizer.from_pretrained(str(TARGET_MODEL))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    model = AutoModelForCausalLM.from_pretrained(
        str(TARGET_MODEL), torch_dtype=torch.bfloat16,
        attn_implementation="sdpa").to("cuda")
    model.config.use_cache = False
    from peft import LoraConfig, get_peft_model
    model = get_peft_model(model, LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM", bias="none"))

    forget_rows = sample_rows(FORGET_FILE, args.n_forget, args.seed, "1")
    retain_rows = sample_rows(RETAIN_FILE, args.n_retain, args.seed, None)
    ref = refusals(REFUSAL_FILE)
    safe_texts = [ref[i % len(ref)] for i in range(len(forget_rows))]
    examples = [encode_example(tok, build_prompt(r["question"], "DefaultCoT"),
                               t, args.max_len)
                for r, t in zip(forget_rows, safe_texts)]
    examples += [encode_example(tok, build_prompt(r["question"], "DefaultCoT"),
                                r["answer"], args.max_len) for r in retain_rows]
    batch = collate(tok, examples)

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad],
                            lr=args.lr)
    t0 = time.time()
    model.train()
    out, meta = method_loss(args.method, model, tok, batch, forget_rows,
                            retain_rows, args.max_len, args.lr, safe_texts)
    out.loss.backward()
    torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 1.0)
    opt.step()
    adapter = out_dir / "adapter"
    model.save_pretrained(str(adapter))
    tok.save_pretrained(str(adapter))
    summary = {
        "diagnostic_only": True,
        "claim_level": "non-claim",
        "method": args.method,
        "run_id": run_id,
        "adapter": str(adapter),
        "n_forget": len(forget_rows),
        "n_retain": len(retain_rows),
        "max_len": args.max_len,
        "lr": args.lr,
        "optimizer_steps": 1,
        "loss": float(out.loss.detach().cpu()),
        "diagnostics": getattr(out, "float_diagnostics", lambda: {})(),
        "meta": meta,
        "elapsed_sec": round(time.time() - t0, 1),
        "note": "one-step diagnostic training; not convergence and not a claim",
    }
    (out_dir / "train_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "train_args.json").write_text(
        json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
