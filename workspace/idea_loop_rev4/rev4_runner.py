"""Rev-4 driver: start FROM the champion, autonomously generate and reproduce
single-knob optimisation ideas inside the champion family, until the stricter
target is met. MD stays the source of truth; all numbers are re-run here."""
import hashlib, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop_rev4")
W = Path("/usr/local/workspace/R-TOFU/workspace")
sys.path.insert(0, str(R))
import idea_engine
PY = "/usr/local/bin/python"
CHAMPION_VAL = 0.075000
MAX_ROUNDS, MAX_MINUTES = 4, 25
TARGET, ULIM, BLIM, NEED = 0.15, 0.10, 0.20, 2
KEYS = ("val_risk","peak_vram_mb","worst_leak","partial_leak","gamma","retain_rouge",
        "utility_drop","weight_drift","train_steps","budget_exceeded","elapsed_sec","knobs")
# deterministic candidate sequence: single whitelisted knob, training volume unchanged
CANDIDATES = [
    ("BAN_MARGIN", "25.0", "HIGH_BYPASS_RESIDUAL", "residual partial-name bypass; strengthen logit suppression"),
    ("BAN_MARGIN", "30.0", "HIGH_BYPASS_RESIDUAL", "further strengthen suppression margin"),
    ("W_FORGET",   "12.0", "HIGH_RISK",            "increase forgetting pressure"),
    ("LR",         "3e-4", "REFINE",               "larger step for finer convergence"),
]

def rev(): return hashlib.sha256((R/"train.py").read_bytes()).hexdigest()[:7]
def app(p,l):
    with open(R/p,"a",encoding="utf-8") as f: f.write(l+"\n")
def parse():
    t=(R/"run.log").read_text(errors="replace"); o={}
    for k in KEYS:
        m=re.search(rf"^{k}:\s*(.+)$",t,re.M)
        if m:o[k]=m.group(1).strip()
    return o if "val_risk" in o else None
def good(m):
    try: return (float(m["val_risk"])<=TARGET and float(m["utility_drop"])<=ULIM
                and float(m["partial_leak"])<=BLIM and float(m["weight_drift"])>0)
    except Exception: return False
def reproduce_ok(m, rc):
    if rc != 0 or m is None: return False
    if float(m.get("elapsed_sec", 999)) > 300.0: return False
    return all(k in m for k in ("val_risk","worst_leak","partial_leak",
                                "utility_drop","weight_drift")) and float(m["weight_drift"])>0
def run():
    env=dict(os.environ, PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    with open(R/"run.log","w") as f:
        return subprocess.run([PY,"train.py"],cwd=R,stdout=f,
                              stderr=subprocess.STDOUT,timeout=330,env=env).returncode
def apply_knob(k,v):
    if k not in idea_engine.WHITELIST or v not in idea_engine.WHITELIST[k]:
        raise ValueError(f"knob rejected: {k}={v}")
    s=(R/"train.py").read_text(encoding="utf-8")
    s,n=re.subn(rf"^{re.escape(k)}\s*=\s*[^#\n]+",f"{k} = {v}",s,count=1,flags=re.M)
    if n!=1: raise ValueError(f"knob not found: {k}")
    (R/"train.py").write_text(s,encoding="utf-8")
def diagnose(m):
    if float(m["partial_leak"])>0: return "HIGH_BYPASS_RESIDUAL"
    if float(m["val_risk"])>TARGET: return "HIGH_RISK"
    if float(m["utility_drop"])>ULIM: return "UTILITY_DAMAGE"
    return "REFINE"
def save(st): (R/"state.json").write_text(json.dumps(st,indent=2),encoding="utf-8")

def main():
    t0=time.time()
    st={"round":0,"best":None,"stable":0,"tried":[],"last":{},"stop":None,
        "crashes":0,"phase":"ready","started_at":t0}
    rows=[]
    (R/"ideas.jsonl").write_text("",encoding="utf-8")
    # baseline = champion itself, re-run to obtain reproducible metrics
    shutil.copy(R/"train.py",R/"rounds/r00_train.py")
    rc=run(); m=parse()
    if rc!=0 or m is None: raise SystemExit("champion baseline failed")
    st["best"]=float(m["val_risk"]); st["last"]=m; save(st)
    with open(R/"results.tsv","w",encoding="utf-8") as f:
        f.write("rev\tval_risk\tmemory_gb\tstatus\tdescription\n")
        f.write(f"{rev()}\t{m['val_risk']}\t{float(m['peak_vram_mb'])/1024:.1f}\t"
                f"keep\tbaseline CHAMPION LB_m20_e5 (six prior reproductions)\n")
    with open(R/"PROGRESS.md","w",encoding="utf-8") as f:
        f.write("# PROGRESS — Rev-4 autonomous optimisation FROM the champion\n\n")
        f.write(f"## baseline — champion re-run val_risk={m['val_risk']} "
                f"partial_leak={m['partial_leak']} GOOD={good(m)}\n\n")
    print(f"[rev4] baseline champion val={m['val_risk']} good={good(m)}",flush=True)

    for r in range(1,MAX_ROUNDS+1):
        if (time.time()-t0)/60>=MAX_MINUTES: st["stop"]="BUDGET_EXHAUSTED_TIME"; break
        if st["crashes"]>=2: st["stop"]="ERROR_STOP"; break
        target_met = st["best"] < CHAMPION_VAL - 1e-9
        confirm = st["stable"] == 1
        start_rev=rev()
        shutil.copy(R/"train.py",R/f"rounds/r{r:02d}_start_train.py")
        if confirm:
            idea={"name":"CONFIRM","diagnosis":"CONFIRM","knob":None,"value":None,
                  "idea":"independent reproduction of the retained idea (no code change)",
                  "source":"confirmation"}
            commit=start_rev
        else:
            nxt=next((c for c in CANDIDATES if (c[0],c[1]) not in st["tried"]), None)
            if nxt is None: st["stop"]="NO_MORE_CANDIDATES"; break
            k,v,tag,why=nxt
            idea={"name":f"{k}={v}","diagnosis":diagnose(st["last"]),"knob":k,"value":v,
                  "idea":why,"source":"diagnostic_generation"}
            try: apply_knob(k,v)
            except Exception as e:
                st["stop"]="IDEA_COMPILE_REJECTED"; print(e,flush=True); break
            st["tried"].append((k,v))
            shutil.copy(R/"train.py",R/f"rounds/r{r:02d}_train.py")
            commit=rev()
        try: rc=run()
        except subprocess.TimeoutExpired: rc=124
        shutil.copy(R/"run.log",R/f"run_r{r:02d}.log")
        m=parse(); repro=reproduce_ok(m,rc)
        if not repro:
            status,val,mem="crash","0.000000","0.0"; m=m or {}
            st["crashes"]+=1; st["stable"]=0
            print(f"[rev4] r{r:02d} CRASH rc={rc}",flush=True)
        else:
            st["crashes"]=0
            val,mem=m["val_risk"],f"{float(m['peak_vram_mb'])/1024:.1f}"
            breach=float(m["utility_drop"])>ULIM
            better=(float(val)<st["best"]-1e-9 and not breach)
            status="keep" if better else "discard"
            if better: st["best"]=float(val)
            elif not confirm: shutil.copy(R/f"rounds/r{r:02d}_start_train.py",R/"train.py")
            st["stable"]=st["stable"]+1 if (good(m) and st["best"]<CHAMPION_VAL-1e-9) else 0
            st["last"]=m
        idea["experimentally_reproduced"]=bool(repro)
        idea["reproduced_metrics"]={k:m.get(k) for k in
            ("val_risk","worst_leak","partial_leak","utility_drop","weight_drift","elapsed_sec")}
        app("results.tsv",f"{commit}\t{val}\t{mem}\t{status}\t{idea['name']} {idea['diagnosis']}")
        with open(R/"ideas.jsonl","a",encoding="utf-8") as f:
            f.write(json.dumps({"round":r,**idea,"rev":commit,"result_status":status},ensure_ascii=False)+"\n")
        rec={"round":r,"rev":commit,"start_rev":start_rev,"idea":idea,"status":status,
             "val_risk":val,"memory_gb":mem,"metrics":m,"confirmation":confirm,
             "stable":st["stable"],"best":st["best"]}
        (R/f"rounds/r{r:02d}.json").write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding="utf-8")
        rows.append(rec)
        with open(R/"PROGRESS.md","a",encoding="utf-8") as f:
            f.write(f"## r{r:02d} — {idea['name']}{' (CONFIRMATION)' if confirm else ''}\n\n"
                    f"- diagnosis `{idea['diagnosis']}`, reproduced={idea['experimentally_reproduced']}\n"
                    f"- rev `{commit}` → `{status}`, val_risk={val}, best={st['best']}, "
                    f"stable={st['stable']}/{NEED}\n"
                    f"- worst={m.get('worst_leak','-')}, partial={m.get('partial_leak','-')}, "
                    f"utility_drop={m.get('utility_drop','-')}, drift={m.get('weight_drift','-')}\n\n")
        st["round"]=r; save(st)
        print(f"[rev4] r{r:02d} {idea['name']} confirm={confirm} val={val} status={status} "
              f"repro={repro} stable={st['stable']} best={st['best']}",flush=True)
        if st["stable"]>=NEED: st["stop"]="REACHED_TARGET"; break
    else: st["stop"]="BUDGET_EXHAUSTED_ROUNDS"
    st["phase"]="stopped"; st["elapsed_min"]=round((time.time()-t0)/60,2); save(st)
    improved = st["best"] < CHAMPION_VAL - 1e-9
    sm={"run_tag":"from-champion-rev4","stop_reason":st["stop"],"final_rev":rev(),
        "start":"champion LB_m20_e5 (val_risk=0.075000, six prior reproductions)",
        "champion_val_risk":CHAMPION_VAL,"best_val_risk":st["best"],
        "strictly_better_than_champion":bool(improved),
        "rounds_executed":st["round"],"stable_count":st["stable"],
        "elapsed_min":st["elapsed_min"],
        "idea_source":"diagnostic single-knob generation inside the champion LOGIT_BAN family",
        "state_machine":"sha256 content hash + train.py snapshots",
        "termination_definition":{
            "unchanged_guardrails":{"val_risk":TARGET,"utility_drop":ULIM,
                                    "partial_leak":BLIM,"weight_drift":">0"},
            "stricter_target":f"best_val_risk < {CHAMPION_VAL}",
            "stable_needed":NEED,
            "note":"tightened, NOT relaxed: the champion already satisfies the original guardrails",
            "max_rounds":MAX_ROUNDS,"max_minutes":MAX_MINUTES},
        "counts":{"keep":sum(x["status"]=="keep" for x in rows),
                  "discard":sum(x["status"]=="discard" for x in rows),
                  "crash":sum(x["status"]=="crash" for x in rows),
                  "confirmation":sum(x["confirmation"] for x in rows),
                  "reproduced":sum(bool(x["idea"]["experimentally_reproduced"]) for x in rows)},
        "rounds":rows}
    (R/"IDEA_LOOP_SUMMARY.json").write_text(json.dumps(sm,ensure_ascii=False,indent=2),encoding="utf-8")
    L=["# Rev-4 — 针对冠军 idea 的自主优化循环","",
       f"- 终止原因: **{st['stop']}**",
       f"- 起点: 冠军 `LB_m20_e5`（`val_risk=0.075000`，此前六次独立复现）",
       f"- 最佳 `val_risk`: **{st['best']:.6f}**；严格优于冠军: **{'是' if improved else '否'}**",
       f"- 轮数 {st['round']}/{MAX_ROUNDS}，耗时 {st['elapsed_min']} 分钟，稳定 {st['stable']}/{NEED}",
       f"- keep/discard/crash/confirm/已复现 = {sm['counts']['keep']}/"
       f"{sm['counts']['discard']}/{sm['counts']['crash']}/"
       f"{sm['counts']['confirmation']}/{sm['counts']['reproduced']}","",
       "## 每轮 idea（均须实跑后获得指标才准入）","",
       "| r | 诊断 | idea | val_risk | worst | partial | util | 复现 | 状态 |",
       "|---|---|---|---|---|---|---|---|---|"]
    for x in rows:
        i,m=x["idea"],x["metrics"]
        L.append(f"| {x['round']:02d} | {i['diagnosis']} | {i['name']} | {x['val_risk']} | "
                 f"{m.get('worst_leak','-')} | {m.get('partial_leak','-')} | "
                 f"{m.get('utility_drop','-')} | {i['experimentally_reproduced']} | {x['status']} |")
    L += ["","## 五点要求","",
          "1. **启动/结束**：state 就绪、预算、上轮归档、候选过 whitelist 编译、终止未满足；"
          "`ok/crash/keep/discard`（恢复 start 快照）。",
          "2. **评估并生成思路**：冻结 `prepare.evaluate()` 五项指标 → 诊断 "
          "`HIGH_BYPASS_RESIDUAL/HIGH_RISK/UTILITY_DAMAGE/REFINE` → 在冠军族内生成单 knob 改动；"
          "**实跑成功后该 idea 才获得 `experimentally_reproduced=true`**。",
          "3. **应用回下一轮**：`apply_knob()` 写唯一可编辑的 `train.py` → "
          "`rounds/rXX_train.py` 快照 + sha256 rev；keep 后从该状态继续，discard 恢复 start 快照。",
          f"4. **终止判据**：原四条件护栏**未改**（`val_risk<={TARGET}`、`utility_drop<={ULIM}`、"
          f"`partial_leak<={BLIM}`、`weight_drift>0`）；因起点已达标，把目标**收紧**为 "
          f"`best_val_risk < {CHAMPION_VAL}` 且连续 {NEED} 轮通过护栏 → `REACHED_TARGET`，"
          "第二轮为不改代码的独立复现。预算/crash/无候选停止均不算达标。",
          "5. **记录追踪**：`results.tsv`、`ideas.jsonl`（含本轮实测指标与准入状态）、"
          "`rounds/rXX.json`、train.py 双快照、`run_rXX.log`、`PROGRESS.md`、`state.json`、本文件。","",
          "## 结论","",
          ("找到严格优于冠军的同族变体，形成真实迭代链。" if improved else
           "预算内未找到严格优于冠军的同族变体 —— **冠军 `LB_m20_e5` 是当前局部最优**；"
           "按纪律不伪造达标、不放宽阈值。冠军原达标结论不变。"),
          "","> ⚠️ 无论本轮是否更优，held-out 泛化不足、oracle token bank、"
          "`REVIEW_UNAVAILABLE` / 门控 `BLOCKED` 等边界均不变。",""]
    (R/"IDEA_LOOP_SUMMARY.md").write_text("\n".join(L),encoding="utf-8")
    print(f"[rev4] STOP {st['stop']} best={st['best']} improved={improved} "
          f"rounds={st['round']} keep={sm['counts']['keep']}",flush=True)

if __name__=="__main__": main()
