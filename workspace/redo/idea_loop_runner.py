"""Driver for the idea-in-the-loop training experiment.

Lives OUTSIDE the experiment repo: train.py remains the only editable file.
Non-blocking by design (AUTO_PROCEED=true): every checkpoint is a state update,
never a question. Resumable via state.json.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
sys.path.insert(0, str(REPO))
import idea_engine  # noqa: E402

PY = "/usr/local/bin/python"
MAX_ROUNDS = 10
MAX_MINUTES = 35
TARGET_RISK = 0.15
UTILITY_LIMIT = 0.10
BYPASS_LIMIT = 0.20
STABLE_NEEDED = 2
IDEA_SOURCE = os.environ.get("IDEA_SOURCE", "deterministic")  # deterministic | llm
KEYS = ("val_risk", "peak_vram_mb", "worst_leak", "partial_leak", "gamma",
        "retain_rouge", "utility_drop", "weight_drift", "train_steps",
        "train_loss_first", "train_loss_last", "knobs", "budget_exceeded",
        "elapsed_sec")


def sh(cmd):
    return subprocess.run(cmd, cwd=REPO, shell=True, capture_output=True, text=True)


def short():
    return sh("git rev-parse --short HEAD").stdout.strip()


def parse_log():
    txt = (REPO / "run.log").read_text(encoding="utf-8", errors="replace")
    out = {}
    for k in KEYS:
        m = re.search(rf"^{k}:\s*(.+)$", txt, re.M)
        if m:
            out[k] = m.group(1).strip()
    return out if "val_risk" in out else None


def append(path, line):
    with open(REPO / path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_state():
    p = REPO / "state.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {"round": 0, "best": 0.950948, "stable_count": 0,
            "no_improve": 0, "consecutive_crash": 0, "phase": "ready",
            "last_metrics": {"worst_leak": 0.95, "partial_leak": 0.0,
                             "gamma": 0.0, "utility_drop": 0.001896},
            "tried": [], "started_at": time.time(), "stop_reason": None}


def save_state(st):
    (REPO / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def good(m):
    return (float(m.get("val_risk", 9)) <= TARGET_RISK
            and float(m.get("utility_drop", 9)) <= UTILITY_LIMIT
            and float(m.get("partial_leak", 9)) <= BYPASS_LIMIT
            and float(m.get("weight_drift", 0)) > 0)


def main():
    st = load_state()
    t_start = st.get("started_at", time.time())
    print(f"[idea-loop] resume round={st['round']} best={st['best']} "
          f"source={IDEA_SOURCE}", flush=True)
    rows = []
    for r in range(st["round"] + 1, MAX_ROUNDS + 1):
        elapsed_min = (time.time() - t_start) / 60
        if elapsed_min >= MAX_MINUTES:
            st["stop_reason"] = "BUDGET_EXHAUSTED_TIME"
            break
        if st["consecutive_crash"] >= 2:
            st["stop_reason"] = "ERROR_STOP"
            break
        dirty = sh("git status --porcelain").stdout.strip()
        if dirty:
            st["stop_reason"] = "ERROR_DIRTY_TREE"
            print("[idea-loop] ABORT dirty:", dirty, flush=True)
            break

        idea = idea_engine.generate(st["last_metrics"], set(map(tuple, st["tried"])),
                                   st["no_improve"], IDEA_SOURCE, rows)
        if not idea["accepted"] or not idea["knob"]:
            st["stop_reason"] = "NO_MORE_IDEAS"
            break
        st["tried"].append([idea["knob"], idea["value"]])
        start_commit = short()
        try:
            new_text = idea_engine.compile_idea(idea, (REPO / "train.py").read_text(encoding="utf-8"))
        except Exception as ex:
            st["stop_reason"] = "IDEA_COMPILE_REJECTED"
            print("[idea-loop] compile rejected", ex, flush=True)
            break
        (REPO / "train.py").write_text(new_text, encoding="utf-8")
        c = sh(f'git add train.py && git commit -m "r{r:02d}: {idea["diagnosis"]} {idea["knob"]}={idea["value"]}"')
        if c.returncode != 0:
            st["stop_reason"] = "COMMIT_FAILED"
            break
        commit = short()

        run = sh(f"timeout 600 {PY} train.py > run.log 2>&1")
        shutil.copy(REPO / "run.log", REPO / f"run_r{r:02d}.log")
        m = parse_log()
        if run.returncode != 0 or m is None:
            status, val, mem = "crash", "0.000000", "0.0"
            st["consecutive_crash"] += 1
            st["no_improve"] += 1
            st["stable_count"] = 0
            print(f"[idea-loop] r{r:02d} CRASH rc={run.returncode}: "
                  f"{(REPO / 'run.log').read_text(errors='replace')[-300:]}", flush=True)
            m = {}
        else:
            st["consecutive_crash"] = 0
            val = m["val_risk"]
            mem = f"{float(m['peak_vram_mb']) / 1024:.1f}"
            over = m.get("budget_exceeded", "0") != "0"
            drift = float(m.get("weight_drift", 0))
            improved = float(val) < st["best"] - 1e-9 and not over and drift > 0
            status = "keep" if improved else "discard"
            if improved:
                st["best"] = float(val)
                st["no_improve"] = 0
            else:
                st["no_improve"] += 1
                print(f"[idea-loop] r{r:02d} discard val={val} best={st['best']} "
                      f"-> reset --hard {start_commit}", flush=True)
                rr = sh(f"git reset --hard {start_commit}")
                if rr.returncode != 0:
                    st["stop_reason"] = "RESET_FAILED"
                    break
            st["stable_count"] = st["stable_count"] + 1 if (good(m) and status == "keep") else 0
            st["last_metrics"] = m

        append("results.tsv", f"{commit}\t{val}\t{mem}\t{status}\t"
                             f"{idea['diagnosis']} {idea['knob']}={idea['value']}")
        with open(REPO / "ideas.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"round": r, **idea, "commit": commit,
                                "result_status": status}, ensure_ascii=False) + "\n")
        rec = {"round": r, "commit": commit, "start_commit": start_commit,
               "idea": idea, "status": status, "val_risk": val,
               "memory_gb": mem, "metrics": m,
               "state": {"best": st["best"], "stable_count": st["stable_count"],
                         "no_improve": st["no_improve"]},
               "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        (REPO / f"rounds/r{r:02d}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(rec)
        with open(REPO / "PROGRESS.md", "a", encoding="utf-8") as f:
            f.write(f"## r{r:02d} — {idea['diagnosis']}\n\n"
                    f"- idea: {idea['idea']} (`{idea['knob']}={idea['value']}`, "
                    f"family={idea['family']}, source={idea['source']})\n"
                    f"- commit `{commit}` → `{status}`, val_risk={val}, "
                    f"best={st['best']}, stable={st['stable_count']}/{STABLE_NEEDED}, "
                    f"no_improve={st['no_improve']}\n"
                    f"- metrics: worst_leak={m.get('worst_leak','-')}, "
                    f"partial_leak={m.get('partial_leak','-')}, "
                    f"utility_drop={m.get('utility_drop','-')}, "
                    f"weight_drift={m.get('weight_drift','-')}\n\n")
        st["round"] = r
        st["phase"] = "running"
        save_state(st)
        print(f"[idea-loop] r{r:02d}/{MAX_ROUNDS} {idea['knob']}={idea['value']} "
              f"val={val} status={status} best={st['best']} "
              f"stable={st['stable_count']} noimp={st['no_improve']}", flush=True)

        if st["stable_count"] >= STABLE_NEEDED:
            st["stop_reason"] = "REACHED_TARGET"
            break
    else:
        st["stop_reason"] = "BUDGET_EXHAUSTED_ROUNDS"

    st["phase"] = "stopped"
    st["elapsed_min"] = round((time.time() - t_start) / 60, 2)
    save_state(st)
    summary = {
        "run_tag": "idealoop23", "branch": sh("git branch --show-current").stdout.strip(),
        "stop_reason": st["stop_reason"], "final_commit": short(),
        "best_val_risk": st["best"], "rounds_executed": st["round"],
        "stable_count": st["stable_count"], "idea_source": IDEA_SOURCE,
        "termination_definition": {
            "target_risk": TARGET_RISK, "utility_limit": UTILITY_LIMIT,
            "bypass_limit": BYPASS_LIMIT, "stable_needed": STABLE_NEEDED,
            "max_rounds": MAX_ROUNDS, "max_minutes": MAX_MINUTES},
        "counts": {"keep": sum(x["status"] == "keep" for x in rows),
                   "discard": sum(x["status"] == "discard" for x in rows),
                   "crash": sum(x["status"] == "crash" for x in rows)},
        "rounds": rows,
    }
    (REPO / "IDEA_LOOP_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# IDEA-IN-THE-LOOP — 自动训练流程结果", "",
             f"- 终止原因: **{st['stop_reason']}**",
             f"- 执行轮数: {st['round']} / {MAX_ROUNDS}；耗时 {st['elapsed_min']} 分钟",
             f"- 最佳 `val_risk`: **{st['best']:.6f}**（目标 ≤ {TARGET_RISK}）",
             f"- 稳定计数: {st['stable_count']}/{STABLE_NEEDED}；"
             f"keep/discard/crash = {summary['counts']['keep']}/"
             f"{summary['counts']['discard']}/{summary['counts']['crash']}",
             f"- 思路来源: `{IDEA_SOURCE}`；最终 commit `{summary['final_commit']}`", "",
             "## 每轮 idea → 结果", "",
             "| r | 诊断 | 优化思路(knob=value) | val_risk | 状态 |",
             "|---|---|---|---|---|"]
    for x in rows:
        lines.append(f"| {x['round']:02d} | {x['idea']['diagnosis']} | "
                     f"{x['idea']['knob']}={x['idea']['value']} | {x['val_risk']} | {x['status']} |")
    lines += ["", "## 终止判据", "",
              f"`val_risk <= {TARGET_RISK}` 且 `utility_drop <= {UTILITY_LIMIT}` 且 "
              f"`partial_leak <= {BYPASS_LIMIT}` 且 `weight_drift > 0`，"
              f"连续 {STABLE_NEEDED} 轮满足 → REACHED_TARGET。",
              "预算耗尽 / 连续 2 次 crash / 无可用 idea 也会停止，但**不算达标**。", "",
              "## 追踪文件", "",
              "`results.tsv`、`ideas.jsonl`、`rounds/rXX.json`、`run_rXX.log`、"
              "`PROGRESS.md`、`state.json`（可 `--resume`）、git 分支上的逐轮 commit。", ""]
    (REPO / "IDEA_LOOP_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[idea-loop] STOP {st['stop_reason']} best={st['best']} "
          f"rounds={st['round']}", flush=True)


if __name__ == "__main__":
    main()
