"""Multi-step pre-training harness with full CSDA/RRBU/CFA/RIPPLE hooks.

This is the integration step before a full-data run. It supports:
  - one or more optimizer steps + grad accumulation
  - full hooks for csda / rrbu / cfa / ripple
  - the existing proxy losses for the other six methods
  - optional reference model for RIPPLE neighbour KL
  - adapter checkpointing and a machine-readable summary
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, "/usr/local/workspace/tracks/lrm-unlearning/redact/workspace")

from data_utils import key_phrase, refusals, sample_rows  # noqa: E402
from paths import (FORGET_FILE, REFUSAL_FILE, RESULTS, RETAIN_FILE, SEED,
                   TARGET_MODEL, ensure_dirs)  # noqa: E402
from strategies import build_prompt  # noqa: E402
from diagnostic_train import (build_batch, collate, encode_example,
                              entity_token_ids, forward, method_loss)  # noqa: E402
from implementations.hooks.bound_hook import BOUNDHook  # noqa: E402
from implementations.hooks.cfa_hook import CFAHook, CFAHookConfig  # noqa: E402
from implementations.hooks.csda_hook import (CSDAHook, CSDAHookConfig,
                                             entity_token_id)  # noqa: E402
from implementations.hooks.disco_hook import DISCOHook  # noqa: E402
from implementations.hooks.eas_hook import EASHook  # noqa: E402
from implementations.hooks.ortho_hook import ORTHOHook, ORTHOHookConfig  # noqa: E402
from implementations.hooks.ripple_hook import (KnowledgeGraph, RIPPLEHook,
                                               RIPPLEHookConfig)  # noqa: E402
from implementations.hooks.rrbu_hook import (RRBUHook, RRBUHookConfig,
                                             attack_eval_split)  # noqa: E402
from implementations.hooks.scope_hook import SCOPEHook  # noqa: E402
from implementations.hooks.sequ_hook import SEQUHook  # noqa: E402


def load_model(tokenizer_only=False, attn_implementation="sdpa"):
    tok = AutoTokenizer.from_pretrained(str(TARGET_MODEL))
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    tok.padding_side = "right"
    if tokenizer_only:
        return tok, None
    model = AutoModelForCausalLM.from_pretrained(
        str(TARGET_MODEL), torch_dtype=torch.bfloat16,
        attn_implementation=attn_implementation).to("cuda")
    model.config.use_cache = False
    return tok, model


def make_batch(tok, forget_rows, retain_rows, safe_texts, max_len):
    examples = [encode_example(tok, build_prompt(r["question"], "DefaultCoT"), t, max_len)
                for r, t in zip(forget_rows, safe_texts)]
    examples += [encode_example(tok, build_prompt(r["question"], "DefaultCoT"),
                                r["answer"], max_len) for r in retain_rows]
    return collate(tok, examples)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True,
                    choices=["csda", "eas", "rrbu", "disco", "ortho", "scope",
                             "sequ", "cfa", "ripple", "bound"])
    ap.add_argument("--run-id", default="")
    ap.add_argument("--steps", type=int, default=1)
    ap.add_argument("--grad-accum", type=int, default=1)
    ap.add_argument("--n-forget", type=int, default=2)
    ap.add_argument("--n-retain", type=int, default=1)
    ap.add_argument("--max-len", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--lora-r", type=int, default=8)
    ap.add_argument("--lora-alpha", type=int, default=32)
    ap.add_argument("--hook-mode", choices=["full", "proxy"], default="full")
    ap.add_argument("--resume", default="", help="optional adapter dir to resume")
    ap.add_argument("--claims", default="/usr/local/workspace/tracks/lrm-unlearning/"
                    "redact/knowledge_banks/forget10/claims.json")
    ap.add_argument("--no-reference", action="store_true")
    args = ap.parse_args()

    ensure_dirs()
    run_id = args.run_id or f"pretrain_{args.method}"
    out_dir = RESULTS / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    tok, model = load_model(
        attn_implementation="eager" if args.method == "rrbu" else "sdpa")
    from peft import LoraConfig, get_peft_model
    model = get_peft_model(model, LoraConfig(
        r=args.lora_r, lora_alpha=args.lora_alpha, lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        task_type="CAUSAL_LM", bias="none"))
    if args.resume:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model.get_base_model(),
                                          args.resume, is_trainable=True)
        print(f"[resume] loaded adapter from {args.resume}", flush=True)
    model.train()
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=args.lr)

    ref_model = None
    if args.method == "ripple" and not args.no_reference:
        ref_model = AutoModelForCausalLM.from_pretrained(
            str(TARGET_MODEL), torch_dtype=torch.bfloat16,
            attn_implementation="sdpa").to("cuda")
        ref_model.config.use_cache = False
        ref_model.eval()

    # initial data
    forget_rows = sample_rows(FORGET_FILE, args.n_forget, args.seed, "1")
    retain_rows = sample_rows(RETAIN_FILE, args.n_retain, args.seed, None)
    ref = refusals(REFUSAL_FILE)
    safe_texts = [ref[i % len(ref)] for i in range(len(forget_rows))]

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
            inner_lr=args.lr, inner_steps=2, create_graph=True))
    elif args.method == "cfa" and args.hook_mode == "full":
        hooks["cfa"] = CFAHook(feature_dim=7, config=CFAHookConfig(), device="cuda")
    elif args.method == "ripple" and args.hook_mode == "full":
        graph = KnowledgeGraph.from_claims_file(args.claims)
        hooks["ripple"] = RIPPLEHook(graph, RIPPLEHookConfig())
        hooks["ripple_graph_entities"] = len(graph.entities())
    elif args.method == "eas" and args.hook_mode == "full":
        claims = json.loads(Path(args.claims).read_text())
        claims = [c for c in claims if isinstance(c, str)]
        hooks["eas"] = EASHook(claims)
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

    losses = []
    meta = {}
    t0 = time.time()
    for step in range(args.steps):
        # deterministic resampling so multi-step runs see different rows
        f_rows = sample_rows(FORGET_FILE, args.n_forget, args.seed + step, "1")
        r_rows = sample_rows(RETAIN_FILE, args.n_retain, args.seed + step, None)
        safe = [ref[i % len(ref)] for i in range(len(f_rows))]
        batch = make_batch(tok, f_rows, r_rows, safe, args.max_len)

        if args.method == "csda" and "csda" in hooks:
            logits, hidden, nll = forward(model, *batch)
            row = f_rows[0]
            out = hooks["csda"].loss(
                build_prompt(row["question"], "DefaultCoT"), row.get("cot", ""),
                entity_token_id(tok, row["answer"]), nll[len(f_rows):].mean())
            meta = {"hook": "full-csda",
                    "retain_stats": "diagonal covariance"}
        elif args.method == "rrbu" and "rrbu" in hooks:
            attack_rows, _ = attack_eval_split(f_rows, max(1, len(f_rows) - 1), args.seed)
            attack_batch = make_batch(tok, attack_rows,
                                      r_rows[:1] if r_rows else r_rows,
                                      [ref[0]] * len(attack_rows), args.max_len)
            retain_batch = make_batch(tok, [], r_rows, [], args.max_len)
            out = hooks["rrbu"].outer_loss(
                hooks["rrbu"].trainable_params(), attack_batch, retain_batch)
            meta = {"hook": "full-rrbu", "inner_steps": 2}
        elif args.method == "cfa" and "cfa" in hooks:
            logits, hidden, nll = forward(model, *batch)
            membership = torch.cat([
                torch.ones(len(f_rows)),
                torch.zeros(len(r_rows)),
            ]).to("cuda").float()
            out = hooks["cfa"].training_loss(
                nll[:len(f_rows)].mean(), nll[len(f_rows):].mean(), hidden, membership)
            meta = {"hook": "full-cfa", "style": "hidden mean/std/norm"}
        elif args.method == "ripple" and "ripple" in hooks:
            logits, hidden, nll = forward(model, *batch)
            ref_logits, ref_hidden, _ = forward(ref_model, *batch)
            nf = len(f_rows)
            nr = len(r_rows)
            out = hooks["ripple"].loss(
                nll[:nf].mean(),
                logits[nf:, -1, :],
                ref_logits[:nr, -1, :],
                hidden[:nf].mean(1),
                ref_hidden[:nf].mean(1),
            )
            meta = {"hook": "full-ripple",
                    "graph_entities": hooks.get("ripple_graph_entities"),
                    "neighbors": "retain batch"}
        elif args.method == "eas" and "eas" in hooks:
            logits, hidden, nll = forward(model, *batch)
            nf = len(f_rows)
            entity = key_phrase(f_rows[0].get("answer", ""))
            feats = hooks["eas"].builder.build(entity, f_rows[0].get("cot", ""))
            eids = entity_token_ids(tok, f_rows)
            out_loss = torch.clamp(
                logits[:nf, -1, :].gather(1, eids.view(-1, 1)).squeeze(1),
                min=0.0)
            out = hooks["eas"].loss(
                nll[:nf], out_loss, nll[nf:].mean().expand(nf),
                feats.kappa.to(logits.device).expand(nf),
                feats.depth.to(logits.device).expand(nf))
            meta = {"hook": "full-eas", "kappa": float(feats.kappa), "depth": float(feats.depth)}
        elif args.method == "disco" and "disco" in hooks:
            logits, hidden, nll = forward(model, *batch)
            nf = len(f_rows)
            batches = hooks["disco"].policy_batches(tok, f_rows, safe, args.max_len)
            policy, bare, names = hooks["disco"].policy_logits(model, batches)
            eids = entity_token_ids(tok, f_rows)
            out = hooks["disco"].loss(policy, bare, eids, nll[nf:].mean())
            meta = {"hook": "full-disco", "policies": names}
        elif args.method == "ortho" and "ortho" in hooks:
            logits, hidden, nll = forward(model, *batch)
            nf = len(f_rows)
            out = hooks["ortho"].loss(
                nll[:nf].mean(), hidden[:nf], hidden[:nf].detach(), -1,
                nll[nf:].mean())
            meta = {"hook": "full-ortho", "subspace_layers": list(hooks["ortho"].bank.subspaces)}
        elif args.method == "scope" and "scope" in hooks:
            logits, hidden, nll = forward(model, *batch)
            nf = len(f_rows)
            step_logits = hooks["scope"].step_logits(logits[:nf])
            out = hooks["scope"].loss(step_logits, step_logits.detach(),
                                      entity_token_ids(tok, f_rows),
                                      nll[nf:].mean())
            meta = {"hook": "full-scope", "variants": hooks["scope"].config.n_variants}
        elif args.method == "sequ" and "sequ" in hooks:
            logits, hidden, nll = forward(model, *batch)
            nf = len(f_rows)
            trainable = {n: p for n, p in model.named_parameters() if p.requires_grad}
            out = hooks["sequ"].loss(nll[:nf].mean(), nll[nf:].mean(),
                                     trainable, trainable)
            meta = {"hook": "full-sequ", "n_batches": hooks["sequ"].config.n_batches}
        elif args.method == "bound" and "bound" in hooks:
            logits, hidden, nll = forward(model, *batch)
            nf = len(f_rows)
            budget_logits = {b: logits[:nf] for b in hooks["bound"].config.budgets}
            exits = hooks["bound"].exit_losses(budget_logits, batch[1][:nf],
                                                nll[:nf].mean())
            out = hooks["bound"].loss(
                [nll[:nf].mean()] * len(exits), list(exits.values()))
            meta = {"hook": "full-bound", "budgets": list(exits)}
        else:
            out, meta = method_loss(args.method, model, tok, batch, f_rows, r_rows,
                                    args.max_len, args.lr, safe)
            meta = {"hook": "proxy", **meta}

        loss = out.loss / max(1, args.grad_accum)
        loss.backward()
        if (step + 1) % args.grad_accum == 0 or step + 1 == args.steps:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            opt.zero_grad(set_to_none=True)
        if args.method == "cfa" and "cfa" in hooks:
            adv_opt = torch.optim.Adam(hooks["cfa"].adversary.parameters(), lr=args.lr)
            hooks["cfa"].update_adversary(hidden.detach(), membership, adv_opt)
        losses.append(float(out.loss.detach().cpu()))
        print(f"[{run_id}] step {step+1}/{args.steps} loss={losses[-1]:.4f}", flush=True)

    adapter = out_dir / "adapter"
    model.save_pretrained(str(adapter))
    tok.save_pretrained(str(adapter))
    summary = {
        "diagnostic_only": True,
        "claim_level": "non-claim",
        "method": args.method,
        "run_id": run_id,
        "adapter": str(adapter),
        "hook_mode": args.hook_mode,
        "steps": args.steps,
        "grad_accum": args.grad_accum,
        "n_forget": args.n_forget,
        "n_retain": args.n_retain,
        "max_len": args.max_len,
        "lr": args.lr,
        "losses": losses,
        "meta": meta,
        "elapsed_sec": round(time.time() - t0, 1),
        "note": "pre-training integration smoke; not convergence and not a claim",
    }
    (out_dir / "train_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "train_args.json").write_text(
        json.dumps(vars(args), ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
