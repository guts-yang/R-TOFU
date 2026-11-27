#!/usr/bin/env python3
"""Summarize one non-claim diagnostic run. Never writes a claim or gate result."""
import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
RESULTS = WORKSPACE / "results"
OUT = Path(__file__).resolve().parent


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--role", default="method")
    args = ap.parse_args()

    eval_sum_path = RESULTS / f"eval_{args.tag}.summary.json"
    judge_sum_path = RESULTS / f"judge_{args.tag}.summary.json"
    eval_rows_path = RESULTS / f"eval_{args.tag}.jsonl"
    judge_rows_path = RESULTS / f"judge_{args.tag}.jsonl"

    out_dir = OUT / args.method
    out_dir.mkdir(parents=True, exist_ok=True)
    for p in (eval_sum_path, judge_sum_path, eval_rows_path, judge_rows_path):
        if p.exists():
            shutil.copy2(p, out_dir / p.name)

    if not eval_sum_path.exists():
        status = "LOAD_OR_JUDGE_FAIL"
        lines = [f"# {args.method} — diagnostic", "", f"Status: **{status}**", "",
                 "Model evaluation did not produce a summary file."]
        (out_dir / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(status)
        return

    ev = load_json(eval_sum_path)
    jd = load_json(judge_sum_path) if judge_sum_path.exists() else {"groups": {}}
    jrows = load_jsonl(judge_rows_path) if judge_rows_path.exists() else []

    forget_groups = {k: v for k, v in ev.get("groups", {}).items() if "forget" in v}
    max_entity_leak = max((v["forget"].get("leak_rate") or 0.0) for v in forget_groups.values()) if forget_groups else None
    retain_rouge = [v.get("retain", {}).get("rouge_mean") for v in ev.get("groups", {}).values()]
    retain_rouge = [x for x in retain_rouge if x is not None]

    judged = sum(v.get("judged", 0) for v in jd.get("groups", {}).values())
    n_judge = sum(v.get("n", 0) for v in jd.get("groups", {}).values())
    coverage = round(judged / n_judge, 4) if n_judge else 0.0
    llm_rates = [v.get("llm_leak_rate") for k, v in jd.get("groups", {}).items()
                 if not k.endswith(":retain") and v.get("llm_leak_rate") is not None]
    max_llm_leak = max(llm_rates) if llm_rates else None
    agree_vals = [v.get("agreement") for v in jd.get("groups", {}).values() if v.get("agreement") is not None]
    agreement = round(sum(agree_vals) / len(agree_vals), 4) if agree_vals else None

    mean_retain = round(sum(retain_rouge) / len(retain_rouge), 4) if retain_rouge else None
    if coverage < 0.5 or max_llm_leak is None:
        status = "LOAD_OR_JUDGE_FAIL"
    elif coverage < 0.8:
        status = "LOW_COVERAGE"
    elif args.method == "target" and max_llm_leak >= 0.5:
        status = "CONTROL_EXPECTED_LEAK"
    elif max_llm_leak <= 0.25 and mean_retain is not None and mean_retain < 0.10:
        status = "COLLAPSE"
    elif max_llm_leak > 0.5:
        status = "FAIL_DIAGNOSTIC"
    elif max_llm_leak <= 0.25 and (agreement is None or agreement >= 0.75):
        status = "PASS_DIAGNOSTIC"
    else:
        status = "WARN_DIAGNOSTIC"

    lines = [
        f"# {args.method} — non-claim diagnostic",
        "",
        f"**Status**: `{status}`  ",
        f"**Tag**: `{args.tag}`  ",
        f"**Timestamp**: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}  ",
        "**Scope**: diagnostic-only; no ARIS gate, no claim, no reviewer verdict.",
        "",
        "## Fixed protocol",
        "",
        f"- Samples: {ev.get('config', {}).get('n_forget')} forget + {ev.get('config', {}).get('n_retain')} retain, seed {ev.get('config', {}).get('seed')}",
        f"- Strategies: {', '.join(ev.get('config', {}).get('strategies', []))}",
        f"- Max new tokens: {ev.get('config', {}).get('max_new_tokens_override')}; dtype: {ev.get('config', {}).get('dtype')}",
        f"- Base: `{ev.get('base')}`",
        f"- Adapter: `{ev.get('adapter')}`",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| max entity-rule leak | {max_entity_leak if max_entity_leak is not None else 'NA'} |",
        f"| max Hy4 leak | {max_llm_leak if max_llm_leak is not None else 'NA'} |",
        f"| Hy4 coverage | {coverage} |",
        f"| Hy4/entity agreement | {agreement if agreement is not None else 'NA'} |",
        f"| mean retain ROUGE-L | {mean_retain if mean_retain is not None else 'NA'} |",
        f"| generation rows | {ev.get('n_rows')} |",
        "",
        "## Per-strategy detail",
        "",
        "| Strategy | entity leak | Hy4 leak | judged/failed | agreement |",
        "|---|---:|---:|---:|---:|",
    ]
    for key, g in sorted(ev.get("groups", {}).items()):
        j = jd.get("groups", {}).get(key, {})
        lines.append(f"| {key} | {g.get('forget', {}).get('leak_rate')} | "
                     f"{j.get('llm_leak_rate', 'NA')} | "
                     f"{j.get('judged', 0)}/{j.get('failed', 0)} | "
                     f"{j.get('agreement', 'NA')} |")
    lines += [
        "",
        "## Conclusion",
        "",
        f"`{status}` is a fixed-sample diagnostic label only. It does not establish "
        "unlearning, utility preservation, statistical significance, or a claim.",
    ]
    (out_dir / "RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(status)


if __name__ == "__main__":
    main()
