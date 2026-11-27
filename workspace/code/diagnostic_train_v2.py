"""v2 trainer: safe-CoT targets + four-strategy consistency + dev early stop."""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
os.environ.setdefault("NVIDIA_TF32_OVERRIDE", "0")

import torch
import torch.nn.functional as F
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, "/usr/local/workspace/tracks/lrm-unlearning/redact/workspace")

from data_utils import key_phrase, read_jsonl  # noqa: E402
from paths import FORGET10_FILE, RETAIN_FILE, RESULTS, SEED, TARGET_MODEL, ensure_dirs  # noqa: E402
from strategies import STRATEGY_ORDER, build_prompt  # noqa: E402
from training_data import (DEFAULT_SAFE_COT, build_strategy_batches,
                           load_forget_rows, safe_target, split_dev)  # noqa: E402
from diagnostic_train import entity_token_ids, forward, method_loss  # noqa: E402
from implementations.hooks.bound_hook import BOUNDHook  # noqa: E402
from implementations.hooks.cfa_hook import CFAHook, CFAHookConfig  # noqa: E402
from implementations.hooks.csda_hook import CSDAHook, CSDAHookConfig, entity_token_id  # noqa: E402
from implementations.hooks.disco_hook import DISCOHook  # noqa: E402
from implementations.hooks.eas_hook import EASHook  # noqa: E402
from implementations.hooks.ortho_hook import ORTHOHook, ORTHOHookConfig  # noqa: E402
from implementations.hooks.ripple_hook import KnowledgeGraph, RIPPLEHook, RIPPLEHookConfig  # noqa: E402
from implementations.hooks.rrbu_hook import RRBUHook, RRBUHookConfig, attack_eval_split  # noqa: E402
from implementations.hooks.scope_hook import SCOPEHook  # noqa: E402
from implementations.hooks.sequ_hook import SEQUHook  # noqa: E402

torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False


def load_model(attn_implementation="sdpa"):
    tok = AutoTokenizer.from_pretrained(str(TARGET_MODEL))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    model = AutoModelForCausalLM.from_pretrained(
        str(TARGET_MODEL), torch_dtype=torch.bfloat16,
        attn_implementation=attn_implementation).to("cuda")
    model.config.use_cache = False
    return tok, model


def sample_rows(rows, n, seed):
    rng = random.Random(seed)
    return rng.sample(list(rows), min(n, len(rows)))


def last_token_logits(logits, mask):
    last = (mask.sum(dim=1) - 1).clamp(min=0)
    idx = torch.arange(logits.shape[0], device=logits.device)
    return logits[idx, last, :]


def consistency_loss(default_logits, default_mask, strategy_logits, strategy_mask):
    a = last_token_logits(default_logits, default_mask).detach()
    b = last_token_logits(strategy_logits, strategy_mask)
    p = F.log_softmax(b.float(), dim=-1)
    q = F.softmax(a.float(), dim=-1)
    return F.kl_div(p, q, reduction="batchmean")


def setup_hooks(args, model, tok, retain_rows):
    hooks = {}
    if args.method == "csda" and args.hook_mode == "full":
        hook = CSDAHook(model, tok, CSDAHookConfig(
            layer=-1, max_steps=12, max_len=args.max_len, device="cuda"))
        hook.collect_retain_stats([
            (build_prompt(r["question"], "DefaultCoT"), r.get("cot", ""))
            for r in retain_rows if r.get("cot")
        ])
        hooks["csda"] = hook
    elif args.method == "rrbu" and args.hook_mode == "full":
        hooks["rrbu"] = RRBUHook(model, RRBUHookConfig(
            inner_lr=args.lr, inner_steps=2, create_graph=False))
    elif args.method == "cfa" and args.hook_mode == "full":
        hooks["cfa"] = CFAHook(feature_dim=7, config=CFAHookConfig(), device="cuda")
    elif args.method == "ripple" and args.hook_mode == "full":
        graph = KnowledgeGraph.from_claims_file(args.claims)
        hooks["ripple"] = RIPPLEHook(graph, RIPPLEHookConfig())
        hooks["ripple_graph_entities"] = len(graph.entities())
    elif args.method == "eas" and args.hook_mode == "full":
        claims = json.loads(Path(args.claims).read_text())
        hooks["eas"] = EASHook([c for c in claims if isinstance(c, str)])
    elif args.method == "disco" and args.hook_mode == "full":
        hooks["disco"] = DISCOHook()
    elif args.method == "ortho" and args.hook_mode == "full":
        ortho_hook = ORTHOHook(ORTHOHookConfig(
            layers=(-1,), k=8, max_len=args.max_len, device="cuda"))
        ortho_hook.collect(model, tok, [
            (build_prompt(r["question"], "DefaultCoT"), r.get("cot", ""))
            for r in retain_rows if r.get("cot")
        ])
        hooks["ortho"] = ortho_hook
    elif args.method == "scope" and args.hook_mode == "full":
        hooks["scope"] = SCOPEHook()
    elif args.method == "sequ" and args.hook_mode == "full":
        hooks["sequ"] = SEQUHook()
    elif args.method == "bound" and args.hook_mode == "full":
        hooks["bound"] = BOUNDHook()
    hooks["retain_pool"] = list(retain_rows)
    if args.method == "sequ" and "sequ" in hooks:
        hooks["stream"] = iter(hooks["sequ"].stream(retain_rows[:max(1, len(retain_rows))]))
    return hooks


def method_output(args, model, tok, hooks, default_batch, f_rows, r_rows, safe_texts):
    batch = default_batch
    logits, hidden, nll = forward(model, *batch)
    nf = len(f_rows)
    if args.method == "csda" and "csda" in hooks:
        row = f_rows[0]
        out = hooks["csda"].loss(
            build_prompt(row["question"], "DefaultCoT"), row.get("cot", ""),
            entity_token_id(tok, row["answer"]), nll[nf:].mean())
        meta = {"hook": "full-csda", "retain_stats": "diagonal covariance"}
    elif args.method == "rrbu" and "rrbu" in hooks:
        attack_rows, _ = attack_eval_split(f_rows, max(1, len(f_rows) - 1), args.seed)
        attack_batch = build_strategy_batches(
            tok, attack_rows, r_rows[:1], ["DefaultCoT"], args.max_len)["DefaultCoT"]
        retain_batch = build_strategy_batches(
            tok, [], r_rows, ["DefaultCoT"], args.max_len)["DefaultCoT"]
        out = hooks["rrbu"].outer_loss(
            hooks["rrbu"].trainable_params(), attack_batch, retain_batch)
        meta = {"hook": "full-rrbu", "inner_steps": 2}
    elif args.method == "cfa" and "cfa" in hooks:
        membership = torch.cat([torch.ones(nf), torch.zeros(len(r_rows))]).to("cuda").float()
        out = hooks["cfa"].training_loss(
            nll[:nf].mean(), nll[nf:].mean(), hidden, membership)
        meta = {"hook": "full-cfa", "style": "hidden mean/std/norm"}
    elif args.method == "ripple" and "ripple" in hooks:
        ref_model = hooks.get("reference_model")
        if ref_model is None:
            ref_logits, ref_hidden = logits.detach(), hidden.detach()
        else:
            ref_logits, ref_hidden, _ = forward(ref_model, *batch)
        entity = key_phrase(f_rows[0].get("answer", ""))
        neighbors = hooks["ripple"].graph.neighbors(entity, args.ripple_hops)
        pool = hooks.get("retain_pool", r_rows)
        cand = [r for r in pool
                if any(n.lower() in (r.get("answer", "") + " " + r.get("question", "")).lower()
                       for n in neighbors)]
        if not cand:
            cand = list(r_rows)
        cand = cand[:max(1, len(r_rows))]
        neighbor_batch = build_strategy_batches(
            tok, [], cand, ["DefaultCoT"], args.max_len)["DefaultCoT"]
        cur_nb, _, _ = forward(model, *neighbor_batch)
        ref_nb = (forward(ref_model, *neighbor_batch)[0]
                  if ref_model is not None else cur_nb.detach())
        out = hooks["ripple"].loss(
            nll[:nf].mean(), cur_nb[:, -1, :], ref_nb[:, -1, :],
            hidden[:nf].mean(1), ref_hidden[:nf].mean(1))
        meta = {"hook": "full-ripple", "graph_entities": hooks.get("ripple_graph_entities"),
                "graph_neighbors": len(neighbors), "neighbor_rows": len(cand)}
    elif args.method == "eas" and "eas" in hooks:
        entity = key_phrase(f_rows[0].get("answer", ""))
        feats = hooks["eas"].builder.build(entity, f_rows[0].get("cot", ""))
        eids = entity_token_ids(tok, f_rows)
        out_loss = torch.clamp(
            logits[:nf, -1, :].gather(1, eids.view(-1, 1)).squeeze(1), min=0.0)
        out = hooks["eas"].loss(
            nll[:nf], out_loss, nll[nf:].mean().expand(nf),
            feats.kappa.to(logits.device).expand(nf),
            feats.depth.to(logits.device).expand(nf))
        meta = {"hook": "full-eas", "kappa": float(feats.kappa), "depth": float(feats.depth)}
    elif args.method == "disco" and "disco" in hooks:
        batches = hooks["disco"].policy_batches(tok, f_rows, safe_texts, args.max_len)
        policy, bare, names = hooks["disco"].policy_logits(model, batches)
        out = hooks["disco"].loss(policy, bare, entity_token_ids(tok, f_rows),
                                  nll[nf:].mean())
        meta = {"hook": "full-disco", "policies": names}
    elif args.method == "ortho" and "ortho" in hooks:
        ref_model = hooks.get("reference_model")
        if ref_model is None:
            base_hidden = hidden[:nf].detach()
        else:
            base_hidden = forward(ref_model, *batch)[1][:nf]
        out = hooks["ortho"].loss(nll[:nf].mean(), hidden[:nf],
                                  base_hidden, -1, nll[nf:].mean())
        meta = {"hook": "full-ortho", "reference_drift": ref_model is not None,
                "subspace_layers": list(hooks["ortho"].bank.subspaces)}
    elif args.method == "scope" and "scope" in hooks:
        step_logits = hooks["scope"].step_logits(logits[:nf])
        out = hooks["scope"].loss(step_logits, step_logits.detach(),
                                  entity_token_ids(tok, f_rows), nll[nf:].mean())
        meta = {"hook": "full-scope", "variants": hooks["scope"].config.n_variants}
    elif args.method == "sequ" and "sequ" in hooks:
        ref_model = hooks.get("reference_model")
        ref_hidden = (forward(ref_model, *batch)[1][:nf]
                      if ref_model is not None else hidden[:nf].detach())
        drift = hooks["sequ"].observe_drift(hidden[:nf].mean(1), ref_hidden.mean(1))
        hooks["sequ"].prev_drift = drift.detach()
        trainable = {n: p for n, p in model.named_parameters() if p.requires_grad}
        out = hooks["sequ"].loss(nll[:nf].mean(), nll[nf:].mean(), trainable, trainable)
        meta = {"hook": "full-sequ", "n_batches": hooks["sequ"].config.n_batches,
                "drift": float(drift.detach().cpu())}
    elif args.method == "bound" and "bound" in hooks:
        exits = {}
        for b in hooks["bound"].config.budgets:
            length = min(int(b), logits.shape[1])
            one = hooks["bound"].exit_losses(
                {b: logits[:nf, :length]}, batch[1][:nf, :length], nll[:nf].mean())
            exits.update(one)
        out = hooks["bound"].loss([nll[:nf].mean()] * len(exits), list(exits.values()))
        meta = {"hook": "full-bound", "budgets": list(exits)}
    else:
        out, meta = method_loss(args.method, model, tok, batch, f_rows, r_rows,
                                args.max_len, args.lr, safe_texts)
        meta = {"hook": "proxy", **meta}
    return out, meta, logits, hidden, nll


def dev_score(args, model, tok, dev_forget, retain_rows):
    if not dev_forget:
        return None
    rows = dev_forget[:20]
    batches = build_strategy_batches(tok, rows, retain_rows[:20],
                                     ["DefaultCoT"], args.max_len)
    _, _, nll = forward(model, *batches["DefaultCoT"])
    nf = len(rows)
    return float((nll[:nf].mean() + nll[nf:].mean()).detach().cpu())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True,
                    choices=["csda", "eas", "rrbu", "disco", "ortho", "scope",
                             "sequ", "cfa", "ripple", "bound"])
    ap.add_argument("--run-id", default="")
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--grad-accum", type=int, default=1)
    ap.add_argument("--n-forget", type=int, default=16)
    ap.add_argument("--n-retain", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--hook-mode", choices=["full", "proxy"], default="full")
    ap.add_argument("--resume", default="")
    ap.add_argument("--claims", default="/usr/local/workspace/tracks/lrm-unlearning/"
                    "redact/knowledge_banks/forget10/claims.json")
    ap.add_argument("--safe-cot-file", default=str(DEFAULT_SAFE_COT))
    ap.add_argument("--strategies", default=",".join(STRATEGY_ORDER))
    ap.add_argument("--consistency-weight", type=float, default=0.1)
    ap.add_argument("--dev-ratio", type=float, default=0.10)
    ap.add_argument("--eval-every", type=int, default=50)
    ap.add_argument("--early-stop-patience", type=int, default=3)
    ap.add_argument("--no-reference", action="store_true")
    ap.add_argument("--ripple-hops", type=int, default=2)
    args = ap.parse_args()

    ensure_dirs()
    run_id = args.run_id or f"v2_{args.method}"
    out_dir = RESULTS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    if "DefaultCoT" not in strategies:
        raise ValueError("DefaultCoT is required for the method-specific branch")

    tok, model = load_model("eager" if args.method == "rrbu" else "sdpa")
    from peft import LoraConfig, get_peft_model, PeftModel
    model = get_peft_model(model, LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM", bias="none"))
    if args.resume:
        model = PeftModel.from_pretrained(model.get_base_model(), args.resume,
                                          is_trainable=True)
        print(f"[resume] {args.resume}", flush=True)
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)

    all_forget = load_forget_rows(FORGET10_FILE, "1", args.safe_cot_file)
    train_forget, dev_forget = split_dev(all_forget, args.dev_ratio, args.seed)
    all_retain = read_jsonl(RETAIN_FILE)
    hooks = setup_hooks(args, model, tok, all_retain[:32])
    if args.method in {"ripple", "ortho", "sequ"} and not args.no_reference:
        hooks["reference_model"] = AutoModelForCausalLM.from_pretrained(
            str(TARGET_MODEL), torch_dtype=torch.bfloat16,
            attn_implementation="sdpa").to("cuda")
        hooks["reference_model"].eval()
    if args.method == "sequ" and "sequ" in hooks:
        hooks["stream"] = iter(hooks["sequ"].stream(train_forget))

    losses, dev_scores = [], []
    meta = {}
    best = None
    no_improve = 0
    t0 = time.time()
    for step in range(args.steps):
        if args.method == "sequ" and "stream" in hooks:
            try:
                stream_batch = next(hooks["stream"])
            except StopIteration:
                hooks["stream"] = iter(hooks["sequ"].stream(train_forget))
                stream_batch = next(hooks["stream"])
            f_rows = sample_rows(stream_batch, args.n_forget, args.seed + step)
        else:
            f_rows = sample_rows(train_forget, args.n_forget, args.seed + step)
        r_rows = sample_rows(all_retain, args.n_retain, args.seed + step)
        safe_texts = [safe_target(r, "DefaultCoT") for r in f_rows]
        strategy_batches = build_strategy_batches(
            tok, f_rows, r_rows, strategies, args.max_len)
        default_batch = strategy_batches["DefaultCoT"]

        out, meta, logits, hidden, nll = method_output(
            args, model, tok, hooks, default_batch, f_rows, r_rows, safe_texts)

        # Multi-strategy forget/retain NLL + last-token consistency.
        extra_forget, extra_retain, consistency = [], [], []
        default_logits = logits
        default_mask = default_batch[2]
        for s in strategies:
            if s == "DefaultCoT":
                extra_forget.append(nll[:len(f_rows)].mean())
                extra_retain.append(nll[len(f_rows):].mean())
                continue
            s_logits, _, s_nll = forward(model, *strategy_batches[s])
            extra_forget.append(s_nll[:len(f_rows)].mean())
            extra_retain.append(s_nll[len(f_rows):].mean())
            consistency.append(consistency_loss(
                default_logits, default_mask, s_logits, strategy_batches[s][2]))
        extra_f = torch.stack(extra_forget).mean()
        extra_r = torch.stack(extra_retain).mean()
        cons = torch.stack(consistency).mean() if consistency else torch.zeros((), device=extra_f.device)
        total = out.loss + 0.5 * extra_f + 0.5 * extra_r + args.consistency_weight * cons

        (total / max(1, args.grad_accum)).backward()
        if (step + 1) % args.grad_accum == 0 or step + 1 == args.steps:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
        if args.method == "cfa" and "cfa" in hooks:
            adv_opt = torch.optim.Adam(hooks["cfa"].adversary.parameters(), lr=args.lr)
            hooks["cfa"].update_adversary(hidden.detach(), torch.cat([
                torch.ones(len(f_rows)), torch.zeros(len(r_rows))]).to("cuda").float(),
                adv_opt)
        losses.append(float(total.detach().cpu()))
        print(f"[{run_id}] step {step+1}/{args.steps} loss={losses[-1]:.4f}", flush=True)

        if (step + 1) % max(1, args.eval_every) == 0 or step + 1 == args.steps:
            score = dev_score(args, model, tok, dev_forget, all_retain)
            if score is not None:
                dev_scores.append({"step": step + 1, "score": score})
                print(f"[{run_id}] dev score={score:.4f}", flush=True)
                if best is None or score < best:
                    best = score
                    no_improve = 0
                    model.save_pretrained(str(out_dir / "adapter_best"))
                else:
                    no_improve += 1
                    if no_improve >= args.early_stop_patience:
                        print(f"[{run_id}] early stop at step {step+1}", flush=True)
                        break

    last = out_dir / "adapter_last"
    model.save_pretrained(str(last))
    tok.save_pretrained(str(last))
    adapter = out_dir / "adapter"
    if (out_dir / "adapter_best").exists():
        shutil.copytree(out_dir / "adapter_best", adapter, dirs_exist_ok=True)
    else:
        shutil.copytree(last, adapter, dirs_exist_ok=True)
    tok.save_pretrained(str(adapter))

    hook_status = "PROXY_FALLBACK" if meta.get("hook") == "proxy" else "FULL"
    summary = {
        "diagnostic_only": True, "claim_level": "non-claim",
        "method": args.method, "run_id": run_id, "adapter": str(adapter),
        "hook_mode": args.hook_mode, "hook_status": hook_status, "steps": args.steps,
        "grad_accum": args.grad_accum, "n_forget": args.n_forget,
        "n_retain": args.n_retain, "max_len": args.max_len, "lr": args.lr,
        "strategies": strategies, "consistency_weight": args.consistency_weight,
        "dev_scores": dev_scores, "best_dev_score": best,
        "losses": losses, "meta": meta,
        "elapsed_sec": round(time.time() - t0, 1),
        "note": "v2 diagnostic training; safe CoT + multi-strategy; not a claim",
    }
    (out_dir / "train_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "train_args.json").write_text(
        json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
