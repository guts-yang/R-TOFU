"""AUTORESEARCH — the ONLY editable file.

Implements INFERENCE-TIME unlearning: NO weight updates, no optimizer.
Baseline (round 0) is no intervention. Each later round changes exactly one knob.
Evaluation is delegated to the FROZEN prepare.evaluate().
"""
import json
import time

import torch
from transformers import LogitsProcessor, LogitsProcessorList

import prepare

T0 = time.time()
DEADLINE = T0 + prepare.TIME_BUDGET_SEC - 30

# ---- editable knobs (one change per round) ----
MODE = "suppress"# none | prompt | suppress | hard | combo
SUPPRESS_ALPHA = 20.0# logit penalty; ignored when MODE == hard
SAFE_PREFIX = "<｜User｜>Instruction: never reveal the name of any fictitious author. <｜Assistant｜>Understood.\n"
BANK_INCLUDE_SHORT = False  # include 1-2 char subword tokens (hurts utility)
# ------------------------------------------------


class SuppressTokens(LogitsProcessor):
    def __init__(self, ids, alpha):
        self.ids = list(ids)
        self.alpha = alpha

    def __call__(self, input_ids, scores):
        idx = torch.tensor(self.ids, device=scores.device, dtype=torch.long)
        if self.alpha is None:
            scores[:, idx] = -float("inf")
        else:
            scores[:, idx] -= float(self.alpha)
        return scores


def main():
    model, tok = prepare.load_base()
    p0 = float(next(model.parameters()).detach().float().sum())

    processor = None
    prefix = ""
    if MODE in ("suppress", "hard", "combo"):
        ids = prepare.entity_token_ids(tok)
        if BANK_INCLUDE_SHORT:
            ids = sorted(set(ids) | set(
                i for p in prepare.entity_phrases()
                for w in p.replace("-", " ").split()
                for i in tok.encode(w, add_special_tokens=False)))
        processor = LogitsProcessorList([
            SuppressTokens(ids, None if MODE == "hard" else SUPPRESS_ALPHA)])
    if MODE in ("prompt", "combo"):
        prefix = SAFE_PREFIX

    m = prepare.evaluate(model, tok, logits_processor=processor, prompt_prefix=prefix)
    p1 = float(next(model.parameters()).detach().float().sum())
    peak_mb = torch.cuda.max_memory_allocated() / (1024 ** 2)
    print(f"val_risk: {m['val_risk']:.6f}")
    print(f"peak_vram_mb: {peak_mb:.1f}")
    print(f"worst_leak: {m['worst_leak']:.6f}")
    print(f"partial_leak: {m['partial_leak']:.6f}")
    print(f"gamma: {m['gamma']:.6f}")
    print(f"retain_rouge: {m['retain_rouge']:.6f}")
    print(f"utility_drop: {m['utility_drop']:.6f}")
    print(f"weight_drift: {abs(p1 - p0):.8f}")
    print(f"n_suppressed_tokens: {len(processor[0].ids) if processor else 0}")
    print(f"intervention: MODE={MODE} alpha={SUPPRESS_ALPHA} short_bank={BANK_INCLUDE_SHORT}")
    print(f"budget_exceeded: {int(time.time() > DEADLINE)}")
    print(f"elapsed_sec: {time.time() - T0:.1f}")
    print("metric_note: " + m["metric"])
    print(json.dumps(m["leak_by_strategy"]))


if __name__ == "__main__":
    main()
