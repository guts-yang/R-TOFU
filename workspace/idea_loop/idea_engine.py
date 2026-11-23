"""FROZEN idea engine: diagnose current result -> propose ONE whitelisted change.

deterministic mode is the default (same input -> same output, fully repeatable).
llm mode optionally calls the Hy4 OpenAI-compatible endpoint in
/usr/local/workspace/.env; it is an IDEA GENERATOR ONLY (same model family as
the executor), never an independent reviewer or gate receipt. Failures fall
back to deterministic so the loop never needs a human.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

WHITELIST = {
    "LR": ["5e-5", "1e-4", "2e-4", "3e-4"],
    "EPOCHS": ["1", "2", "3", "4", "5"],
    "W_FORGET": ["0.5", "1.0", "2.0", "4.0", "8.0", "12.0"],
    "W_RETAIN": ["0.5", "1.0", "2.0"],
    "INV_LAMBDA": ["0.0", "0.5", "2.0", "5.0"],
    "LORA_R": ["4", "8", "16"],
    "GA_CLIP": ["4.0", "8.0", "12.0"],
    "LOSS_TYPE": ['"GA_GD"', '"IDK_SFT"', '"TARGETED_GA"', '"CONTRAST"',
                  '"ENTITY_SWAP"', '"DISTILL"', '"LOGIT_BAN"'],
    "BYPASS_TOKENS": ["False", "True"],
    "BAN_MARGIN": ["20.0", "22.0", "25.0", "30.0"],
    "BAN_EXPANDED": ["False", "True"],
    "N_TRAIN": ["48", "96", "144", "192"],
}
FAMILIES = ["suppression", "utility", "bypass", "invariance", "structure"]
ENV_FILE = Path("/usr/local/workspace/.env")
ENDPOINT = "https://tokenlink.woa.com/openapi/v1/chat/completions"

# fixed-priority diagnostic rule table
RULES = [
    ("HIGH_BYPASS", "bypass", "partial_leak", 0.20,
     [("BAN_MARGIN", "25.0"), ("BAN_MARGIN", "30.0"), ("BYPASS_TOKENS", "True")],
     "partial-name leakage is high; include surname/subword tokens in the forgetting target"),
    ("UTILITY_DAMAGE", "utility", "utility_drop", 0.10,
     [("W_RETAIN", "2.0"), ("LR", "5e-5")],
     "retain utility degraded; strengthen retain loss or lower learning rate"),
    ("HIGH_LEAK", "suppression", "worst_leak", 0.30,
     [("W_FORGET", "2.0"), ("W_FORGET", "4.0"), ("EPOCHS", "2"), ("GA_CLIP", "12.0")],
     "target knowledge still leaks; increase gradient-ascent pressure"),
    ("CROSS_STRATEGY_GAP", "invariance", "gamma", 0.10,
     [("INV_LAMBDA", "0.5"), ("INV_LAMBDA", "2.0")],
     "leakage differs across decoding strategies; add consistency penalty"),
]


def diagnose(m, no_improve):
    if no_improve >= 3:
        return ("STAGNATION", "structure",
                [("LOSS_TYPE", '"IDK_SFT"'), ("LORA_R", "16"), ("EPOCHS", "3")],
                "no improvement for 3 rounds; force a structural pivot")
    for tag, fam, key, thr, cands, why in RULES:
        if float(m.get(key, 0)) > thr:
            return (tag, fam, cands, why)
    return ("REFINE", "refine",
            [("BAN_MARGIN", "22.0"), ("BAN_MARGIN", "25.0"), ("W_RETAIN", "2.0")],
            "all hard thresholds met; small conservative refinement of suppression strength")


def _pick(cands, tried, forced_family):
    for k, v in cands:
        if (k, v) not in tried and k in WHITELIST and v in WHITELIST[k]:
            return k, v
    # family-level structural fallback (never repeats a tried pair)
    for k in ("W_FORGET", "EPOCHS", "LORA_R", "INV_LAMBDA", "W_RETAIN", "LR"):
        for v in WHITELIST[k]:
            if (k, v) not in tried:
                return k, v
    return None, None


def generate(m, tried, no_improve, source="deterministic", history=None):
    tag, fam, cands, why = diagnose(m, no_improve)
    k, v = _pick(cands, tried, fam)
    base = {"diagnosis": tag, "family": fam, "idea": why, "knob": k, "value": v,
            "rationale": why, "source": "deterministic", "accepted": k is not None}
    if source != "llm" or k is None:
        return base
    try:
        cfg = {}
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                a, b = line.split("=", 1)
                if a.strip() == "Hy4_TOKEN":
                    cfg["token"] = b.strip().strip('"').strip("'")
        token = os.environ.get("Hy4_TOKEN") or cfg.get("token")
        if not token:
            return base
        prompt = ("You propose ONE training-idea change for an automated loop. "
                  "Return ONLY JSON: {\"idea\": str, \"knob\": str, \"value\": str, \"rationale\": str}.\n"
                  f"Diagnosis: {tag}. Metrics: {json.dumps(m)}.\n"
                  f"Recent history: {json.dumps((history or [])[-3:])}.\n"
                  f"Allowed knobs and values: {json.dumps(WHITELIST)}.")
        body = json.dumps({"model": "hy4", "messages": [{"role": "user", "content": prompt}],
                           "stream": False, "temperature": 0.0}, ensure_ascii=False).encode()
        req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Authorization": f"Bearer {token}",
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=40) as r:
            d = json.loads(r.read())
        obj = json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "",
                                d["choices"][0]["message"]["content"].strip()).strip())
        kk, vv = str(obj["knob"]), str(obj["value"])
        if kk in WHITELIST and vv in WHITELIST[kk] and (kk, vv) not in tried:
            base.update({"idea": str(obj.get("idea", why)), "knob": kk, "value": vv,
                         "rationale": str(obj.get("rationale", why)), "source": "llm",
                         "accepted": True})
        else:
            base["llm_note"] = "proposal rejected by whitelist; deterministic fallback used"
    except Exception as e:
        base["llm_note"] = f"{type(e).__name__}: {str(e)[:80]}; deterministic fallback used"
    return base


def compile_idea(idea, train_text):
    """Apply exactly one whitelisted knob. Refuse anything else."""
    k, v = idea["knob"], idea["value"]
    if k not in WHITELIST or v not in WHITELIST[k]:
        raise ValueError(f"idea rejected: {k}={v} not in whitelist")
    pat = re.compile(rf"^{re.escape(k)}\s*=\s*[^#\n]+", re.M)
    new, n = pat.subn(f"{k} = {v}", train_text, count=1)
    if n != 1:
        raise ValueError(f"knob {k} not found exactly once")
    return new
