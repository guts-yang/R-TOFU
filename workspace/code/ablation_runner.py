#!/usr/bin/env python3
"""Small single-variable ablation runner for v2.

Default is dry-run; pass --execute to launch one short dev-scale diagnostic run.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path("/usr/local/workspace/tracks/lrm-unlearning/R-TOFU/workspace")
CODE = ROOT / "code"
PY = "/jizhicfs/chenyliao/ops/venvs/r-tofu-ga/bin/python"

MATRIX = {
    ("csda", "mask"): ["on", "off"],
    ("csda", "lambda"): ["0.01", "0.1", "0.5"],
    ("eas", "alpha"): ["fixed", "dynamic"],
    ("rrbu", "inner_k"): ["0", "1", "3"],
    ("disco", "policies"): ["2", "5"],
    ("ortho", "k"): ["8", "32"],
    ("ortho", "drift"): ["on", "off"],
    ("scope", "mask"): ["on", "off"],
    ("sequ", "delta"): ["0.05", "0.1", "0.2"],
    ("cfa", "beta"): ["0", "0.1", "0.3"],
    ("ripple", "hops"): ["0", "1", "2"],
    ("bound", "budgets"): ["single", "multi"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", required=True)
    ap.add_argument("--ablation", required=True)
    ap.add_argument("--value", required=True)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--n-forget", type=int, default=4)
    ap.add_argument("--n-retain", type=int, default=4)
    ap.add_argument("--execute", action="store_true")
    args = ap.parse_args()

    key = (args.method, args.ablation)
    if key not in MATRIX:
        raise SystemExit(f"unknown ablation {key}; choose from {sorted(MATRIX)}")
    if args.value not in MATRIX[key]:
        raise SystemExit(f"value {args.value} not in {MATRIX[key]}")

    run_id = f"v2_ablate_{args.method}_{args.ablation}_{args.value}"
    cmd = [
        PY, str(CODE / "diagnostic_train_v2.py"),
        "--method", args.method, "--steps", str(args.steps),
        "--n-forget", str(args.n_forget), "--n-retain", str(args.n_retain),
        "--max-len", "256", "--lr", "1e-4", "--eval-every", str(args.steps),
        "--run-id", run_id, "--hook-mode", "full",
    ]
    print(" ".join(cmd))
    if args.execute:
        subprocess.run(cmd, check=False)


if __name__ == "__main__":
    main()
