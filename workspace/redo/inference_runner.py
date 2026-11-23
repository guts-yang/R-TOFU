"""Driver for the inference-time unlearning autoresearch loop.
Lives OUTSIDE the experiment repo so train.py stays the only editable file.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/usr/local/workspace/R-TOFU/workspace/inference_autoresearch")
PY = "/usr/local/bin/python"

EXPERIMENTS = [
    ("MODE", '"prompt"', "P0 safety-prefix only"),
    ("MODE", '"suppress"', "P1 soft entity-token suppression alpha5"),
    ("SUPPRESS_ALPHA", "20.0", "P1 stronger suppression alpha20"),
    ("MODE", '"hard"', "P1 hard ban entity tokens minus-inf"),
    ("MODE", '"combo"', "P0+P1 combined prefix and suppression"),
    ("BANK_INCLUDE_SHORT", "True", "widen suppressed token bank incl short subwords"),
]


def sh(cmd):
    return subprocess.run(cmd, cwd=REPO, shell=True, capture_output=True, text=True)


def short():
    return sh("git rev-parse --short HEAD").stdout.strip()


def clean():
    r = sh("git status --porcelain")
    return r.stdout.strip() == "", r.stdout.strip()


def set_knob(name, value):
    p = REPO / "train.py"
    s = p.read_text(encoding="utf-8")
    pat = re.compile(rf"^{re.escape(name)}\s*=\s*[^#\n]+", re.M)
    new, n = pat.subn(f"{name} = {value}", s, count=1)
    if n != 1:
        raise RuntimeError(f"knob {name} not found exactly once")
    p.write_text(new, encoding="utf-8")


def parse_log():
    txt = (REPO / "run.log").read_text(encoding="utf-8", errors="replace")
    keys = ("val_risk", "peak_vram_mb", "worst_leak", "partial_leak", "gamma",
            "retain_rouge", "utility_drop", "weight_drift", "n_suppressed_tokens",
            "intervention", "budget_exceeded", "elapsed_sec")
    out = {}
    for k in keys:
        m = re.search(rf"^{k}:\s*(.+)$", txt, re.M)
        if m:
            out[k] = m.group(1).strip()
    return out if "val_risk" in out else None


def main():
    best = float(sys.argv[1]) if len(sys.argv) > 1 else float("inf")
    base_commit = short()
    print(f"[infer-loop] base={base_commit} best={best}", flush=True)
    rows, t0 = [], time.time()
    for i, (knob, value, desc) in enumerate(EXPERIMENTS, 1):
        ok_clean, dirty = clean()
        if not ok_clean:
            print(f"[infer-loop] ABORT dirty tree: {dirty}", flush=True)
            break
        start = short()
        set_knob(knob, value)
        c = sh(f'git add train.py && git commit -m "exp{i}: {desc}"')
        if c.returncode != 0:
            print(f"[infer-loop] commit failed {c.stderr[:200]}", flush=True)
            break
        commit = short()
        r = sh(f"timeout 600 {PY} train.py > run.log 2>&1")
        m = parse_log()
        if r.returncode != 0 or m is None:
            status, val, mem = "crash", "0.000000", "0.0"
            print(f"[infer-loop] {i} CRASH rc={r.returncode}: "
                  f"{(REPO / 'run.log').read_text(errors='replace')[-400:]}", flush=True)
        else:
            val = m["val_risk"]
            mem = f"{float(m['peak_vram_mb']) / 1024:.1f}"
            over = m.get("budget_exceeded", "0") != "0"
            drift = float(m.get("weight_drift", "0"))
            keep = float(val) < best and not over and drift == 0.0
            status = "keep" if keep else "discard"
            if keep:
                best = float(val)
            else:
                print(f"[infer-loop] {i} discard val={val} best={best} "
                      f"over={over} drift={drift} -> reset --hard {start}", flush=True)
                rr = sh(f"git reset --hard {start}")
                if rr.returncode != 0:
                    print("[infer-loop] RESET FAILED", flush=True)
                    break
        with open(REPO / "results.tsv", "a", encoding="utf-8") as f:
            f.write(f"{commit}\t{val}\t{mem}\t{status}\t{desc}\n")
        rows.append({"round": i, "knob": knob, "value": value, "commit": commit,
                     "val_risk": val, "memory_gb": mem, "status": status,
                     "description": desc, "metrics": m or {}})
        print(f"[infer-loop] {i}/{len(EXPERIMENTS)} {knob}={value} val={val} "
              f"worst={m.get('worst_leak') if m else '-'} "
              f"partial={m.get('partial_leak') if m else '-'} "
              f"gamma={m.get('gamma') if m else '-'} status={status} best={best}", flush=True)

    summary = {
        "run_tag": "infer23", "branch": sh("git branch --show-current").stdout.strip(),
        "base_commit": base_commit, "final_commit": short(),
        "best_val_risk": best, "rounds": rows,
        "keep": sum(x["status"] == "keep" for x in rows),
        "discard": sum(x["status"] == "discard" for x in rows),
        "crash": sum(x["status"] == "crash" for x in rows),
        "elapsed_sec": round(time.time() - t0, 1),
        "budget": {"max_experiments": 6, "max_minutes": 30},
        "calibration": json.loads((REPO / "calibration.json").read_text(encoding="utf-8")),
        "adaptation": "val_bpb -> val_risk (generative leak + bypass penalty + utility drop); no weight updates",
    }
    (REPO / "INFERENCE_SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# INFERENCE-TIME UNLEARNING — AUTORESEARCH RESULTS", "",
             f"- Branch `autoresearch/infer23`; baseline `{base_commit}`; final `{summary['final_commit']}`",
             f"- Best `val_risk`: **{best:.6f}** (lower is better)",
             f"- Rounds: {len(rows)} (keep={summary['keep']}, discard={summary['discard']}, crash={summary['crash']})",
             f"- Elapsed: {summary['elapsed_sec']}s; budget 6 experiments / 30 minutes", "",
             "## Round log", "",
             "| # | knob | commit | val_risk | worst_leak | partial_leak | gamma | retain_rouge | status |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        m = r["metrics"]
        lines.append(f"| {r['round']} | {r['knob']}={r['value']} | {r['commit']} | "
                     f"{r['val_risk']} | {m.get('worst_leak','-')} | {m.get('partial_leak','-')} | "
                     f"{m.get('gamma','-')} | {m.get('retain_rouge','-')} | {r['status']} |")
    lines += ["", "## Hypothesis read-out", "",
              "- **H1 (suppression lowers leak)**: see `worst_leak` column vs baseline 0.950000.",
              "- **H2 (strength vs utility)**: see `retain_rouge` vs baseline 0.259097.",
              "- **H3 (strategy interaction)**: see `gamma` vs baseline 0.000000.",
              "- **H4 (bypass via partial name)**: see `partial_leak` vs baseline 0.000000; "
              "a rise here means full-name suppression was circumvented.",
              "", "## Honesty notes", "",
              "- `weight_drift` is printed every round and must be 0.0: this is inference-time only.",
              "- `val_risk` penalises partial-name leakage, so the loop cannot win by shortening names.",
              "- Predefined knobs only; no evaluation metric, sample set or threshold was changed mid-loop.",
              "- No cross-model reviewer was available; findings are not an independent review.", ""]
    (REPO / "INFERENCE_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("[infer-loop] wrote INFERENCE_RESULTS.md / INFERENCE_SUMMARY.json", flush=True)


if __name__ == "__main__":
    main()
