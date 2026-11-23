"""Path registry. All code/results live under WORKSPACE; datasets and models are read-only."""
from pathlib import Path

WORKSPACE = Path("/usr/local/workspace/R-TOFU/workspace")
REPO = Path("/usr/local/workspace/R-TOFU")
ASU_ROOT = Path("/jizhicfs/chenyliao")

CODE = WORKSPACE / "code"
RESULTS = WORKSPACE / "results"
LOGS = WORKSPACE / "logs"
REFINE_LOGS = WORKSPACE / "refine-logs"

DATA = ASU_ROOT / "data" / "rtofu"
MODELS = ASU_ROOT / "models"
CKPT = ASU_ROOT / "checkpoints"

TARGET_MODEL = MODELS / "sangyon" / "LRM-target"
REFUSAL_FILE = REPO / "data" / "idontknow.jsonl"
FORGET_FILE = DATA / "forget01.json"
RETAIN_FILE = DATA / "retain90.json"

R2MU_MODELS = {
    "r2mu01": CKPT / "r2mu-forget01" / "checkpoint-last",
    "r2mu05": CKPT / "r2mu-forget05" / "checkpoint-last",
    "r2mu10": CKPT / "r2mu-forget10" / "checkpoint-last",
}

ADAPTER_RUNS = {
    "ours-inv": RESULTS / "ours-inv",
    "ctrl-single": RESULTS / "ctrl-single",
    "inv-lambda0": RESULTS / "inv-lambda0",
    "inv-lambda2": RESULTS / "inv-lambda2",
}

SEED = 1001


def resolve_model(system: str):
    """Return (base_model_path, adapter_path_or_None)."""
    if system == "target":
        return TARGET_MODEL, None
    if system in R2MU_MODELS:
        return R2MU_MODELS[system], None
    if system in ADAPTER_RUNS:
        return TARGET_MODEL, ADAPTER_RUNS[system] / "adapter"
    raise ValueError(f"unknown system: {system}; available: target, {list(R2MU_MODELS)}, {list(ADAPTER_RUNS)}")


def ensure_dirs():
    for d in (RESULTS, LOGS):
        d.mkdir(parents=True, exist_ok=True)
