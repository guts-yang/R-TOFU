"""Non-claim diagnostic evaluation for any base model or merged checkpoint.

This harness deliberately does NOT write claim-level artifacts. It emits a small
fixed-sample JSONL + summary that downstream Hy4 metric judging can consume.
Ground truth is always the R-TOFU gold answer.
"""
import argparse
import json
import time

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from data_utils import sample_rows
from decode_eval import _clean, eval_group, generate_batch
from paths import FORGET_FILE, RESULTS, RETAIN_FILE, SEED, ensure_dirs
from strategies import STRATEGY_ORDER, max_new_tokens


def load_any(base, adapter, dtype):
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
    if adapter:
        model = PeftModel.from_pretrained(model, str(adapter))
    model.eval()
    return model, tok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--adapter", default="")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--n-forget", type=int, default=4)
    ap.add_argument("--n-retain", type=int, default=2)
    ap.add_argument("--forget-task-id", default="1")
    ap.add_argument("--strategies", default="DefaultCoT,ZeroThink")
    ap.add_argument("--max-new-tokens", type=int, default=128)
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--forget-file", default=str(FORGET_FILE))
    ap.add_argument("--retain-file", default=str(RETAIN_FILE))
    ap.add_argument("--dtype", default="fp32", choices=["fp32", "bf16", "fp16"])
    args = ap.parse_args()

    ensure_dirs()
    strategies = [s.strip() for s in args.strategies.split(",") if s.strip()]
    model, tok = load_any(args.base, args.adapter or None, args.dtype)
    forget_rows = sample_rows(args.forget_file, args.n_forget, args.seed, args.forget_task_id)
    retain_rows = sample_rows(args.retain_file, args.n_retain, args.seed, None)

    all_rows, groups = [], {}
    t0 = time.time()
    for strategy in strategies:
        n_new = max_new_tokens(strategy, args.max_new_tokens)
        fr, fg = eval_group(model, tok, forget_rows, strategy, n_new,
                            args.system, args.tag, False, 0, args.batch_size)
        rr, rg = eval_group(model, tok, retain_rows, strategy, n_new,
                            args.system, args.tag, True, 0, args.batch_size)
        for x in rr:
            x["strategy"] = f"{strategy}:retain"
        all_rows.extend(fr + rr)
        groups[strategy] = {"forget": fg, "retain": rg}
        print(f"[{args.tag}] {strategy}: forget leak={fg.get('leak_rate')} "
              f"retain rouge={rg.get('rouge_mean')} "
              f"truncated={fg.get('truncated_rate')}", flush=True)

    leak_rates = [g["forget"]["leak_rate"] for g in groups.values()
                  if g.get("forget", {}).get("n")]
    summary = {
        "diagnostic_only": True,
        "claim_level": "non-claim",
        "note": "fixed small-sample diagnostic; not a significance test, not a reviewer verdict",
        "system": args.system,
        "tag": args.tag,
        "base": args.base,
        "adapter": args.adapter or None,
        "config": {
            "n_forget": len(forget_rows),
            "n_retain": len(retain_rows),
            "forget_task_id": args.forget_task_id,
            "strategies": strategies,
            "max_new_tokens_override": args.max_new_tokens,
            "seed": args.seed,
            "do_sample": False,
            "dtype": args.dtype,
        },
        "groups": groups,
        "gamma": round(max(leak_rates) - min(leak_rates), 6) if leak_rates else None,
        "max_leak": round(max(leak_rates), 6) if leak_rates else None,
        "n_rows": len(all_rows),
        "elapsed_sec": round(time.time() - t0, 1),
    }

    jsonl_path = RESULTS / f"eval_{args.tag}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_path = RESULTS / f"eval_{args.tag}.summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[{args.tag}] wrote {jsonl_path} and {summary_path}", flush=True)


if __name__ == "__main__":
    main()
