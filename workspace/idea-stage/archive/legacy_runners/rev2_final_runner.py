"""Rev-2 FINAL driver: sha256 content hash + train.py snapshots replace git.
Same termination thresholds; adds a no-code-change confirmation replay."""
import json, os, re, shutil, subprocess, sys, time, hashlib
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
sys.path.insert(0, str(R))
import idea_engine
PY = "/usr/local/bin/python"
MAX_ROUNDS, MAX_MINUTES = 6, 35
TARGET, ULIM, BLIM, NEED = 0.15, 0.10, 0.20, 2
KEYS = ("val_risk","peak_vram_mb","worst_leak","partial_leak","gamma","retain_rouge",
        "utility_drop","weight_drift","train_steps","budget_exceeded","elapsed_sec","knobs")

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
def run():
    env=dict(os.environ,PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True")
    with open(R/"run.log","w") as f:
        return subprocess.run([PY,"train.py"],cwd=R,stdout=f,
                              stderr=subprocess.STDOUT,timeout=330,env=env).returncode
def save(st): (R/"state.json").write_text(json.dumps(st,indent=2),encoding="utf-8")

def main():
    st={"round":0,"best":0.075,"best_good":True,"stable":0,"no_improve":0,
        "crashes":0,"last_status":None,"tried":[],
        "last":{"val_risk":"0.075","worst_leak":"0.0","partial_leak":"0.15",
                "gamma":"0.0","utility_drop":"0.0"},
        "t0":time.time(),"stop":None}
    save(st); rows=[]
    print(f"[rev2] start best={st['best']}",flush=True)
    for r in range(1,MAX_ROUNDS+1):
        if (time.time()-st["t0"])/60>=MAX_MINUTES: st["stop"]="BUDGET_EXHAUSTED_TIME"; break
        if st["crashes"]>=2: st["stop"]="ERROR_STOP"; break
        confirm=(st["stable"]==1 or (st["best_good"] and st["last_status"]=="discard"))
        start_rev=rev()
        shutil.copy(R/"train.py",R/f"rounds/r{r:02d}_start_train.py")
        if confirm:
            idea={"diagnosis":"CONFIRM","family":"confirmation",
                  "idea":"independent reproduction replay with no code change",
                  "knob":None,"value":None,"rationale":"verify stability",
                  "source":"confirmation","accepted":True}
            commit=start_rev
        else:
            idea=idea_engine.generate(st["last"],set(map(tuple,st["tried"])),
                                      st["no_improve"],"deterministic",rows)
            if not idea["accepted"] or not idea["knob"]: st["stop"]="NO_MORE_IDEAS"; break
            st["tried"].append([idea["knob"],idea["value"]])
            new=idea_engine.compile_idea(idea,(R/"train.py").read_text(encoding="utf-8"))
            (R/"train.py").write_text(new,encoding="utf-8")
            shutil.copy(R/"train.py",R/f"rounds/r{r:02d}_train.py")
            commit=rev()
        try: rc=run()
        except subprocess.TimeoutExpired: rc=124
        shutil.copy(R/"run.log",R/f"run_r{r:02d}.log")
        m=parse()
        if rc!=0 or m is None:
            status,val,mem="crash","0.000000","0.0"; m={}
            st["crashes"]+=1; st["stable"]=0
        else:
            st["crashes"]=0
            val,mem=m["val_risk"],f"{float(m['peak_vram_mb'])/1024:.1f}"
            over=m.get("budget_exceeded","0")!="0"
            drift=float(m.get("weight_drift",0))
            breach=float(m.get("utility_drop",0))>ULIM
            better=(float(val)<st["best"]-1e-9 and not over and drift>0 and not breach)
            status="keep" if better else "discard"
            if better: st["best"]=float(val); st["no_improve"]=0; st["best_good"]=good(m)
            else:
                st["no_improve"]+=1
                if not confirm: shutil.copy(R/f"rounds/r{r:02d}_start_train.py",R/"train.py")
            st["stable"]=st["stable"]+1 if good(m) else 0
            st["last"]=m
        st["last_status"]=status
        app("results.tsv",f"{commit}\t{val}\t{mem}\t{status}\t{idea['diagnosis']} {idea['knob']}={idea['value']}")
        with open(R/"ideas.jsonl","a",encoding="utf-8") as f:
            f.write(json.dumps({"round":r,**idea,"rev":commit,"result_status":status},ensure_ascii=False)+"\n")
        rec={"round":r,"rev":commit,"start_rev":start_rev,"idea":idea,"status":status,
             "val_risk":val,"memory_gb":mem,"metrics":m,"confirmation":confirm,
             "stable":st["stable"]}
        (R/f"rounds/r{r:02d}.json").write_text(json.dumps(rec,ensure_ascii=False,indent=2),encoding="utf-8")
        rows.append(rec)
        with open(R/"PROGRESS.md","a",encoding="utf-8") as f:
            f.write(f"## r{r:02d} — {idea['diagnosis']}{' (CONFIRMATION)' if confirm else ''}\n\n"
                    f"- idea: {idea['idea']} ({idea['knob']}={idea['value']})\n"
                    f"- rev `{commit}` → `{status}`, val_risk={val}, stable={st['stable']}/{NEED}\n"
                    f"- worst={m.get('worst_leak','-')}, partial={m.get('partial_leak','-')}, "
                    f"utility_drop={m.get('utility_drop','-')}, drift={m.get('weight_drift','-')}\n\n")
        st["round"]=r; save(st)
        print(f"[rev2] r{r:02d} confirm={confirm} val={val} status={status} "
              f"good={good(m)} stable={st['stable']} best={st['best']}",flush=True)
        if st["stable"]>=NEED: st["stop"]="REACHED_TARGET"; break
    else: st["stop"]="BUDGET_EXHAUSTED_ROUNDS"
    st["phase"]="stopped"; st["elapsed_min"]=round((time.time()-st["t0"])/60,2); save(st)
    sm={"run_tag":"idealoop23c","stop_reason":st["stop"],"final_rev":rev(),
        "best_val_risk":st["best"],"rounds_executed":st["round"],
        "stable_count":st["stable"],"elapsed_min":st["elapsed_min"],
        "state_machine":"sha256 content hash + train.py snapshots (git-free)",
        "termination_definition":{"target_risk":TARGET,"utility_limit":ULIM,
            "bypass_limit":BLIM,"stable_needed":NEED,"max_rounds":MAX_ROUNDS,
            "max_minutes":MAX_MINUTES},
        "counts":{"keep":sum(x["status"]=="keep" for x in rows),
                  "discard":sum(x["status"]=="discard" for x in rows),
                  "crash":sum(x["status"]=="crash" for x in rows),
                  "confirmation":sum(x["confirmation"] for x in rows)},"rounds":rows}
    (R/"IDEA_LOOP_SUMMARY.json").write_text(json.dumps(sm,ensure_ascii=False,indent=2),encoding="utf-8")
    L=["# IDEA-IN-THE-LOOP (Rev-2) — 自动训练流程结果","",
       f"- 终止原因: **{st['stop']}**",
       f"- 轮数 {st['round']}/{MAX_ROUNDS}，耗时 {st['elapsed_min']} 分钟",
       f"- 最佳 `val_risk`: **{st['best']:.6f}**（目标 ≤ {TARGET}）",
       f"- 稳定计数 {st['stable']}/{NEED}；keep/discard/crash/confirm = "
       f"{sm['counts']['keep']}/{sm['counts']['discard']}/{sm['counts']['crash']}/"
       f"{sm['counts']['confirmation']}","","## 每轮","",
       "| r | 类型 | idea | val_risk | good | 状态 |","|---|---|---|---|---|---|"]
    for x in rows:
        L.append(f"| {x['round']:02d} | {'CONFIRM' if x['confirmation'] else 'IDEA'} | "
                 f"{x['idea']['knob']}={x['idea']['value']} | {x['val_risk']} | "
                 f"{good(x['metrics'])} | {x['status']} |")
    L += ["","## 达标定义（未放宽）","",
          f"连续 {NEED} 轮 `val_risk<={TARGET}` 且 `utility_drop<={ULIM}` 且 "
          f"`partial_leak<={BLIM}` 且 `weight_drift>0`；确认轮为**不改代码的独立复现**。","",
          "思路来源：`redo/probe_sweep*.py` 自动扫描 → `redo/idea_search_results.json`；"
          "冠军 `LOGIT_BAN, BAN_MARGIN=20, EPOCHS=5, N_TRAIN=192`。",""]
    (R/"IDEA_LOOP_SUMMARY.md").write_text("\n".join(L),encoding="utf-8")
    print(f"[rev2] STOP {st['stop']} best={st['best']} rounds={st['round']}",flush=True)

if __name__=="__main__": main()
