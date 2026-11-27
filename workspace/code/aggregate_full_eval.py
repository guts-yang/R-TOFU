#!/usr/bin/env python3
"""Aggregate full evaluation summaries into one comparison table."""
import json
from pathlib import Path

ROOT = Path("/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace")
RESULTS = ROOT / "results"
OUT = ROOT / "diagnostics" / "FULL_EVAL_TABLE.md"
METHODS = ["csda", "eas", "rrbu", "disco", "ortho", "scope", "sequ", "cfa", "ripple", "bound"]
STRATEGIES = ["DefaultCoT", "LessThink", "ZeroThink", "SummaryThink"]


def load(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def main():
    rows = []
    for m in METHODS:
        tag = f"fullEval_{m}"
        ev = load(RESULTS / f"eval_{tag}.summary.json")
        jd = load(RESULTS / f"judge_{tag}.summary.json")
        if ev is None:
            rows.append({"method": m, "status": "NO_EVAL"})
            continue
        forget = {}
        retain = []
        for key, g in ev.get("groups", {}).items():
            r = g.get("retain", {}).get("rouge_mean")
            if r is not None:
                retain.append(r)
            if not key.endswith(":retain"):
                forget[key] = g.get("forget", {}).get("leak_rate")
        entity_max = max([v for v in forget.values() if v is not None], default=None)
        gamma = None
        vals = [v for v in forget.values() if v is not None]
        if vals:
            gamma = max(vals) - min(vals)
        jgroups = (jd or {}).get("groups", {})
        jrates = [v.get("llm_leak_rate") for v in jgroups.values()
                  if v.get("llm_leak_rate") is not None]
        judged = sum(v.get("judged", 0) for v in jgroups.values())
        njudge = sum(v.get("n", 0) for v in jgroups.values())
        rows.append({
            "method": m,
            "status": "DONE" if jd is not None else "EVAL_ONLY",
            "entity_max": entity_max,
            "gamma": gamma,
            "hy4_max": max(jrates) if jrates else None,
            "hy4_coverage": round(judged / njudge, 4) if njudge else None,
            "retain_rouge": round(sum(retain) / len(retain), 4) if retain else None,
        })

    lines = [
        "# Full Evaluation Comparison",
        "",
        "| Method | Status | max entity leak | Γ | max Hy4 leak | Hy4 coverage | retain ROUGE-L |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        def f(x):
            return "NA" if x is None else f"{x:.4f}"
        lines.append(
            f"| {r['method']} | {r['status']} | {f(r.get('entity_max'))} | "
            f"{f(r.get('gamma'))} | {f(r.get('hy4_max'))} | "
            f"{f(r.get('hy4_coverage'))} | {f(r.get('retain_rouge'))} |")
    lines += [
        "",
        "Γ = max strategy leakage - min strategy leakage.",
        "Hy4 is a metric judge, not a reviewer. No row here is a claim.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
