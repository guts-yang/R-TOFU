"""Driver for the adapted autoresearch loop. Lives OUTSIDE the experiment repo
so that `train.py` remains the only editable code file inside it.

Rules enforced: one knob per round, log redirected, results.tsv untracked,
keep only strictly lower val_risk, otherwise reset --hard to start_commit
on this clean dedicated branch.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/usr/local/workspace/R-TOFU/workspace/autoresearch")
LOGS = Path("/usr/local/workspace/R-TOFU/workspace/logs")
PY = "/usr/local/bin/python"

EXPERIMENTS = [
    ("INV_LAMBDA", "0.5", "add cross-strategy consistency penalty lambda0.5"),
    ("INV_LAMBDA", "2.0", "stronger consistency penalty lambda2.0"),
    ("W_RETAIN", "2.0", "strengthen retain loss weight to 2.0"),
    ("LORA_R", "16", "increase LoRA rank to 16"),
    ("LR", "3e-4", "raise learning rate to 3e-4"),
    ("GA_CLIP", "4.0", "lower gradient-ascent NLL clip to 4.0"),
]


def sh(cmd, cwd=REPO):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)


def git_status_clean():
    r = sh("git status --porcelain")
    return r.stdout.strip() == "", r.stdout.strip()


def short_commit():
    return sh("git rev-parse --short HEAD").stdout.strip()


def set_knob(name, value):
    p = REPO / "train.py"
    s = p.read_text(encoding="utf-8")
    pat = re.compile(rf"^{re.escape(name)}\s*=\s*[^#\n]+", re.M)
    new, n = pat.subn(f"{name} = {value}", s, count=1)
    if n != 1:
        raise RuntimeError(f"knob {name} not found exactly once")
    p.write_text(new, encoding="utf-8")


def parse_log():
    p = REPO / "run.log"
    if not p.exists():
        return None
    txt = p.read_text(encoding="utf-8", errors="replace")
    out = {}
    for key in ("val_risk", "peak_vram_mb", "worst_leak", "gamma",
                "retain_nll", "train_steps", "budget_exceeded", "elapsed_sec"):
        m = re.search(rf"^{key}:\s*(.+)$", txt, re.M)
        if m:
            out[key] = m.group(1).strip()
    return out if "val_risk" in out else None


def append_tsv(commit, val, mem, status, desc):
    with open(REPO / "results.tsv", "a", encoding="utf-8") as f:
        f.write(f"{commit}\t{val}\t{mem}\t{status}\t{desc}\n")


def main():
    best = float(sys.argv[1]) if len(sys.argv) > 1 else float("inf")
    baseline_commit = short_commit()
    print(f"[loop] baseline_commit={baseline_commit} best={best}", flush=True)
    rows = []
    t0 = time.time()
    for i, (knob, value, desc) in enumerate(EXPERIMENTS, 1):
        clean, dirty = git_status_clean()
        if not clean:
            print(f"[loop] ABORT: uncommitted changes: {dirty}", flush=True)
            break
        start = short_commit()
        set_knob(knob, value)
        c = sh(f'git add train.py && git commit -m "exp{i}: {desc}"')
        if c.returncode != 0:
            print(f"[loop] commit failed: {c.stderr[:200]}", flush=True)
            break
        commit = short_commit()
        r = sh(f"timeout 600 {PY} train.py > run.log 2>&1")
        m = parse_log()
        if r.returncode != 0 or m is None:
            status, val, mem = "crash", "0.000000", "0.0"
            print(f"[loop] {i} CRASH rc={r.returncode}: "
                  f"{(REPO / 'run.log').read_text(errors='replace')[-300:]}", flush=True)
        else:
            val = m["val_risk"]
            mem = f"{float(m['peak_vram_mb']) / 1024:.1f}"
            over = m.get("budget_exceeded", "0") != "0"
            ok = (float(val) < best) and not over
            status = "keep" if ok else "discard"
            if ok:
                best = float(val)
            else:
                print(f"[loop] {i} discard (val={val} best={best} over={over}) "
                      f"-> reset --hard {start}", flush=True)
                rr = sh(f"git reset --hard {start}")
                if rr.returncode != 0:
                    print("[loop] RESET FAILED, stopping", flush=True)
                    break
        append_tsv(commit, val, mem, status, desc)
        rows.append({"round": i, "knob": knob, "value": value, "commit": commit,
                     "val_risk": val, "memory_gb": mem, "status": status,
                     "description": desc,
                     "metrics": m or {}})
        print(f"[loop] {i}/{len(EXPERIMENTS)} {knob}={value} "
              f"val={val} status={status} best={best}", flush=True)

    summary = {
        "run_tag": "nov23",
        "branch": sh("git branch --show-current").stdout.strip(),
        "baseline_commit": baseline_commit,
        "final_commit": short_commit(),
        "best_val_risk": best,
        "rounds": rows,
        "keep": sum(r["status"] == "keep" for r in rows),
        "discard": sum(r["status"] == "discard" for r in rows),
        "crash": sum(r["status"] == "crash" for r in rows),
        "elapsed_sec": round(time.time() - t0, 1),
        "budget": {"max_experiments": 6, "max_minutes": 45},
        "adaptation": "val_bpb -> val_risk (teacher-forced leak likelihood); uv run -> python",
        "gate0": json.loads((REPO / "gate_status.json").read_text(encoding="utf-8")),
    }
    (REPO / "AUTORESEARCH_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# AUTORESEARCH SUMMARY", "",
        f"- Run tag: `nov23` / branch `autoresearch/nov23`",
        f"- Baseline commit: `{baseline_commit}`; final commit: `{summary['final_commit']}`",
        f"- Best `val_risk`: **{best:.6f}** (lower is better)",
        f"- Rounds: {len(rows)} (keep={summary['keep']}, discard={summary['discard']}, "
        f"crash={summary['crash']})",
        f"- Elapsed: {summary['elapsed_sec']}s; budget max_experiments=6 / max_minutes=45",
        "", "## Round log", "",
        "| # | knob | commit | val_risk | memory_gb | status | description |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['round']} | {r['knob']}={r['value']} | {r['commit']} | "
                     f"{r['val_risk']} | {r['memory_gb']} | {r['status']} | {r['description']} |")
    lines += ["", "## Adaptation & honesty notes", "",
              "- Original autoresearch optimises `val_bpb` on a small GPT; this run keeps all "
              "structural constraints (single editable file, 300s budget, single metric, "
              "results.tsv untracked, commit/reset) but uses `val_risk` from frozen "
              "`prepare.evaluate()` because the research target is LRM unlearning.",
              "- `val_risk` is a **teacher-forced leakage likelihood**, not generative rho_d. "
              "The shipped `LRM-target` could not reproduce the fiction under any decoding "
              "setting (gold-answer NLL 5.4692); Stage A injected the knowledge and merged a "
              "reproducible base (gold NLL 0.5984, Gate-0 pass).",
              "- Preflight run was voided for train/eval overlap; see `PREFLIGHT_NOTE.md`.",
              "- Remaining limitation: retain train/eval rows partially overlap, so "
              "`utility_drop` may be under-estimated.",
              "- No cross-model reviewer was available; this summary is not a reviewed claim.",
              ""]
    (REPO / "AUTORESEARCH_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print("[loop] wrote AUTORESEARCH_SUMMARY.md / .json", flush=True)


if __name__ == "__main__":
    main()
