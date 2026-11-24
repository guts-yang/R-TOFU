"""Revision-2 driver: starts from the idea-search champion, keeps the SAME
termination thresholds, and adds an automatic independent confirmation replay
so 'stable 2 rounds' is a real reproduction check, not a formality.
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
MAX_ROUNDS = 6
MAX_MINUTES = 35
TARGET_RISK = 0.15
UTILITY_LIMIT = 0.10
BYPASS_LIMIT = 0.20
STABLE_NEEDED = 2
IDEA_SOURCE = "deterministic"
KEYS = ("val_risk", "peak_vram_mb", "worst_leak", "partial_leak", "gamma",
        "retain_rouge", "utility_drop", "weight_drift", "train_steps",
        "budget_exceeded", "elapsed_sec", "knobs")


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


def good(m):
    return (float(m.get("val_risk", 9)) <= TARGET_RISK
            and float(m.get("utility_drop", 9)) <= UTILITY_LIMIT
            and float(m.get("partial_leak", 9)) <= BYPASS_LIMIT
            and float(m.get("weight_drift", 0)) > 0)


def initial_state():
    return {"round": 0, "best": 0.075000, "best_good": True,
            "stable_count": 0, "no_improve": 0, "consecutive_crash": 0,
            "phase": "ready", "last_status": None, "tried": [],
            "last_metrics": {"val_risk": "0.075000", "worst_leak": "0.000000",
                             "partial_leak": "0.150000", "gamma": "0.000000",
                             "utility_drop": "0.000000"},
            "started_at": time.time(), "stop_reason": None}


def save(st):
    (REPO / "state.json").write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def run_train():
    env = dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    return subprocess.run([PY, "train.py"], cwd=REPO,
                          stdout=open(REPO / "run.log", "w"),
                          stderr=subprocess.STDOUT, timeout=330, env=env)


def main():
    st = initial_state()   # fresh run; old ledger archived separately
    save(st)
    t_start = st["started_at"]
    print(f"[loop2] start best={st['best']} (champion from idea search)", flush=True)
    rows = []
    for r in range(1, MAX_ROUNDS + 1):
        if (time.time() - t_start) / 60 >= MAX_MINUTES:
            st["stop_reason"] = "BUDGET_EXHAUSTED_TIME"; break
        if st["consecutive_crash"] >= 2:
            st["stop_reason"] = "ERROR_STOP"; break
        dirty = sh("git status --porcelain").stdout.strip()
        if dirty:
            st["stop_reason"] = "ERROR_DIRTY_TREE"
            print("[loop2] dirty:", dirty, flush=True); break

        confirm = (st["stable_count"] == 1 or
                   (st["best_good"] and st.get("last_status") == "discard"))
        start_commit = short()
        if confirm:
            idea = {"diagnosis": "CONFIRM", "family": "confirmation",
                    "idea": "independent reproduction replay with no code change",
                    "knob": None, "value": None, "rationale": "verify stability",
                    "source": "confirmation", "accepted": True}
            commit = start_commit
        else:
            idea = idea_engine.generate(st["last_metrics"],
                                        set(map(tuple, st["tried"])),
                                        st["no_improve"], IDEA_SOURCE, rows)
            if not idea["accepted"] or not idea["knob"]:
                st["stop_reason"] = "NO_MORE_IDEAS"; break
            st["tried"].append([idea["knob"], idea["value"]])
            try:
                new = idea_engine.compile_idea(
                    idea, (REPO / "train.py").read_text(encoding="utf-8"))
            except Exception as ex:
                st["stop_reason"] = "IDEA_COMPILE_REJECTED"
                print("[loop2] compile rejected", ex, flush=True); break
            (REPO / "train.py").write_text(new, encoding="utf-8")
            c = sh('git add train.py && git commit -m '
                   f'"r{r:02d}: {idea["diagnosis"]} {idea["knob"]}={idea["value"]}"')
            if c.returncode != 0:
                st["stop_reason"] = "COMMIT_FAILED"; break
            commit = short()

        try:
            run = run_train()
            rc = run.returncode
        except subprocess.TimeoutExpired:
            rc = 124
        shutil.copy(REPO / "run.log", REPO / f"run_r{r:02d}.log")
        m = parse_log()
        if rc != 0 or m is None:
            status, val, mem = "crash", "0.000000", "0.0"
            st["consecutive_crash"] += 1
            st["stable_count"] = 0
            m = {}
            print(f"[loop2] r{r:02d} CRASH rc={rc}", flush=True)
        else:
            st["consecutive_crash"] = 0
            val, mem = m["val_risk"], f"{float(m['peak_vram_mb']) / 1024:.1f}"
            over = m.get("budget_exceeded", "0") != "0"
            drift = float(m.get("weight_drift", 0))
            guard_breach = float(m.get("utility_drop", 0)) > UTILITY_LIMIT
            improved = (float(val) < st["best"] - 1e-9 and not over and drift > 0
                        and not guard_breach)
            status = "keep" if improved else "discard"
            if improved:
                st["best"] = float(val)
                st["no_improve"] = 0
                st["best_good"] = good(m)
            else:
                st["no_improve"] += 1
                if not confirm:
                    print(f"[loop2] r{r:02d} discard val={val} -> reset --hard {start_commit}", flush=True)
                    sh(f"git reset --hard {start_commit}")
            st["stable_count"] = st["stable_count"] + 1 if good(m) else 0
            st["last_metrics"] = m
        st["last_status"] = status

        append("results.tsv", f"{commit}\t{val}\t{mem}\t{status}\t"
                             f"{idea['diagnosis']} {idea['knob']}={idea['value']}")
        with open(REPO / "ideas.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"round": r, **idea, "commit": commit,
                                "result_status": status}, ensure_ascii=False) + "\n")
        rec = {"round": r, "commit": commit, "idea": idea, "status": status,
               "val_risk": val, "memory_gb": mem, "metrics": m,
               "confirmation": confirm,
               "state": {"best": st["best"], "stable_count": st["stable_count"]}}
        (REPO / f"rounds/r{r:02d}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append(rec)
        with open(REPO / "PROGRESS.md", "a", encoding="utf-8") as f:
            f.write(f"## r{r:02d} — {idea['diagnosis']}{' (CONFIRMATION)' if confirm else ''}\n\n"
                    f"- idea: {idea['idea']} ({idea['knob']}={idea['value']})\n"
                    f"- commit `{commit}` → `{status}`, val_risk={val}, "
                    f"stable={st['stable_count']}/{STABLE_NEEDED}, best={st['best']}\n"
                    f"- worst_leak={m.get('worst_leak','-')}, partial_leak={m.get('partial_leak','-')}, "
                    f"utility_drop={m.get('utility_drop','-')}, weight_drift={m.get('weight_drift','-')}\n\n")
        st["round"] = r
        save(st)
        print(f"[loop2] r{r:02d} confirm={confirm} val={val} status={status} "
              f"good={good(m)} stable={st['stable_count']} best={st['best']}", flush=True)
        if st["stable_count"] >= STABLE_NEEDED:
            st["stop_reason"] = "REACHED_TARGET"; break
    else:
        st["stop_reason"] = "BUDGET_EXHAUSTED_ROUNDS"

    st["phase"] = "stopped"
    st["elapsed_min"] = round((time.time() - t_start) / 60, 2)
    save(st)
    summary = {
        "run_tag": "idealoop23c", "branch": sh("git branch --show-current").stdout.strip(),
        "stop_reason": st["stop_reason"], "final_commit": short(),
        "best_val_risk": st["best"], "rounds_executed": st["round"],
        "stable_count": st["stable_count"], "idea_source": "deterministic+idea-search",
        "termination_definition": {"target_risk": TARGET_RISK, "utility_limit": UTILITY_LIMIT,
                                   "bypass_limit": BYPASS_LIMIT, "stable_needed": STABLE_NEEDED,
                                   "max_rounds": MAX_ROUNDS, "max_minutes": MAX_MINUTES},
        "counts": {"keep": sum(x["status"] == "keep" for x in rows),
                   "discard": sum(x["status"] == "discard" for x in rows),
                   "crash": sum(x["status"] == "crash" for x in rows),
                   "confirmation": sum(x["confirmation"] for x in rows)},
        "rounds": rows,
    }
    (REPO / "IDEA_LOOP_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# IDEA-IN-THE-LOOP (Rev-2) — 自动训练流程结果", "",
             f"- 终止原因: **{st['stop_reason']}**",
             f"- 轮数 {st['round']}/{MAX_ROUNDS}，耗时 {st['elapsed_min']} 分钟",
             f"- 最佳 `val_risk`: **{st['best']:.6f}**（目标 ≤ {TARGET_RISK}）",
             f"- 稳定计数 {st['stable_count']}/{STABLE_NEEDED}；"
             f"keep/discard/crash/confirm = "
             f"{summary['counts']['keep']}/{summary['counts']['discard']}/"
             f"{summary['counts']['crash']}/{summary['counts']['confirmation']}", "",
             "## 每轮", "", "| r | 类型 | idea | val_risk | good | 状态 |",
             "|---|---|---|---|---|---|"]
    for x in rows:
        lines.append(f"| {x['round']:02d} | {'CONFIRM' if x['confirmation'] else 'IDEA'} | "
                     f"{x['idea']['knob']}={x['idea']['value']} | {x['val_risk']} | "
                     f"{good(x['metrics'])} | {x['status']} |")
    lines += ["", "## 达标定义（未放宽）", "",
              f"连续 {STABLE_NEEDED} 轮 `val_risk<={TARGET_RISK}` 且 "
              f"`utility_drop<={UTILITY_LIMIT}` 且 `partial_leak<={BYPASS_LIMIT}` 且 "
              "`weight_drift>0`；确认轮为**不改代码的独立复现**。", "",
              "思路来源：`redo/probe_sweep*.py` 自动扫描 16+ 个训练思路 → "
              "`redo/idea_search_results.json`；冠军配置为 "
              "`LOSS_TYPE=LOGIT_BAN, BAN_MARGIN=20, EPOCHS=5, N_TRAIN=192`。", ""]
    (REPO / "IDEA_LOOP_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"[loop2] STOP {st['stop_reason']} best={st['best']} rounds={st['round']}", flush=True)


if __name__ == "__main__":
    main()
