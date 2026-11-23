import importlib.util, re, sys
from pathlib import Path
R = Path("/usr/local/workspace/R-TOFU/workspace/idea_loop")
sys.path.insert(0, str(R))
src = (R / "train.py").read_text(encoding="utf-8")
for k, v in {"LOSS_TYPE": '"LOGIT_BAN"', "EPOCHS": "2", "W_FORGET": "2.0",
             "W_RETAIN": "1.0", "LR": "1e-4", "N_TRAIN": "96"}.items():
    src, n = re.subn(rf"^{re.escape(k)}\s*=\s*[^#\n]+", f"{k} = {v}", src, count=1, flags=re.M)
    assert n == 1
(R / "probe_train.py").write_text(src, encoding="utf-8")
import prepare
CAP = []
orig = prepare.generate
def spy(tok, model, prompts, logits_processor=None):
    out = orig(tok, model, prompts, logits_processor)
    CAP.extend(zip(prompts, out))
    return out
prepare.generate = spy
spec = importlib.util.spec_from_file_location("probe_mod", R / "probe_train.py")
m = importlib.util.module_from_spec(spec)
sys.modules["probe_mod"] = m
spec.loader.exec_module(m)
m.main()
rows = prepare.read_rows(prepare.FORGET, prepare.N_FORGET)
print("\n===== SAMPLE OUTPUTS (ZeroThink strategy, first forget block) =====")
for i, (p, t) in enumerate(CAP[len(prepare.STRATEGIES)*0:][:6]):
    r = rows[i] if i < len(rows) else rows[0]
    from data_utils import key_phrase
    kp = key_phrase(r["answer"])
    subs = prepare.subwords(kp)
    print(f"[{i}] gold={r['answer'][:90]!r}")
    print(f"     entity={kp!r} subs={subs}")
    print(f"     out  ={t[:200]!r}")
(R / "probe_train.py").unlink(missing_ok=True)
