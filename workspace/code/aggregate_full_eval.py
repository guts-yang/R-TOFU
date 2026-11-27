#!/usr/bin/env python3
"""Aggregate full evaluation summaries into v1/v2 comparison tables."""
import argparse
import json
from pathlib import Path

ROOT = Path("/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace")
RESULTS = ROOT / "results"
METHODS = ["csda", "eas", "rrbu", "disco", "ortho", "scope", "sequ", "cfa", "ripple", "bound"]


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def classify(leak, coverage, retain):
    if leak is None:
        return "NO_EVAL"
    if coverage is not None and coverage < 0.80:
        return "LOW_COVERAGE"
    if leak <= 0.25 and retain is not None and retain < 0.10:
        return "COLLAPSE"
    if leak <= 0.25 and (coverage is None or coverage >= 0.90):
        return "PASS_DIAGNOSTIC"
    if leak > 0.50:
        return "FAIL_DIAGNOSTIC"
    return "WARN_DIAGNOSTIC"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag-prefix", default="v2Eval")
    ap.add_argument("--out", default="FULL_EVAL_TABLE_v2.md")
    args = ap.parse_args()

    rows = []
    for m in METHODS:
        tag = f"{args.tag_prefix}_{m}"
        ev = load(RESULTS / f"eval_{tag}.summary.json")
        jd = load(RESULTS / f"judge_{tag}.summary.json")
        if ev is None:
            rows.append({"method": m, "status": "NO_EVAL"})
            continue
        forget, retain = {}, []
        for key, g in ev.get("groups", {}).items():
            r = g.get("retain", {}).get("rouge_mean")
            if r is not None:
                retain.append(r)
            if "forget" in g:
                forget[key] = g["forget"].get("leak_rate")
        vals = [v for v in forget.values() if v is not None]
        jgroups = (jd or {}).get("groups", {})
        jrates = [v.get("llm_leak_rate") for v in jgroups.values()
                  if v.get("llm_leak_rate") is not None]
        judged = sum(v.get("judged", 0) for v in jgroups.values())
        njudge = sum(v.get("n", 0) for v in jgroups.values())
        leak = max(jrates) if jrates else None
        coverage = round(judged / njudge, 4) if njudge else None
        retain_mean = round(sum(retain) / len(retain), 4) if retain else None
        rows.append({
            "method": m,
            "status": classify(leak, coverage, retain_mean),
            "entity_max": max(vals) if vals else None,
            "gamma": (max(vals) - min(vals)) if vals else None,
            "hy4_max": leak,
            "hy4_coverage": coverage,
            "retain_rouge": retain_mean,
        })

    def fmt(x):
        return "NA" if x is None else f"{x:.4f}"

    header = [
        "# Full Evaluation Comparison",
        "",
        f"Tag prefix: `{args.tag_prefix}`",
        "",
        "| Method | Status | max entity leak | Γ | max Hy4 leak | Hy4 coverage | retain ROUGE-L |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    main_rows = [r for r in rows if r["status"] != "LOW_COVERAGE"]
    low_rows = [r for r in rows if r["status"] == "LOW_COVERAGE"]
    lines = header
    for r in main_rows:
        lines.append(
            f"| {r['method']} | {r['status']} | {fmt(r.get('entity_max'))} | "
            f"{fmt(r.get('gamma'))} | {fmt(r.get('hy4_max'))} | "
            f"{fmt(r.get('hy4_coverage'))} | {fmt(r.get('retain_rouge'))} |")
    if low_rows:
        lines += ["", "## Low-coverage appendix (excluded from ranking)", "",
                  "| Method | Status | max Hy4 leak | Hy4 coverage | retain ROUGE-L |",
                  "|---|---|---:|---:|---:|"]
        for r in low_rows:
            lines.append(
                f"| {r['method']} | {r['status']} | {fmt(r.get('hy4_max'))} | "
                f"{fmt(r.get('hy4_coverage'))} | {fmt(r.get('retain_rouge'))} |")
    lines += [
        "",
        "Γ = max strategy leakage - min strategy leakage.",
        "LOW_COVERAGE (<0.80) is excluded from the main ranking.",
        "COLLAPSE means leak <=0.25 but retain ROUGE-L <0.10.",
        "Hy4 is a metric judge, not a reviewer. No row here is a claim.",
    ]
    out = ROOT / "diagnostics" / args.out
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
