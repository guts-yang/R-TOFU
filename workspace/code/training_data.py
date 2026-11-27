"""v2 training data: safe-CoT targets, four-strategy batches, dev split.

The v1 trainer supervised only the final refusal. v2 supervises the safe CoT
for DefaultCoT and the safe answer for the prefilled strategies, then builds
one batch per strategy for the consistency loss.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import torch

from data_utils import read_jsonl
from strategies import STRATEGY_ORDER, build_prompt

DEFAULT_SAFE_COT = Path(
    "/usr/local/workspace/tracks/lrm-unlearning/redact/data/reasoned_idk/"
    "reasoned_idk_forget10.json"
)


def _norm_question(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def load_safe_cot(path: str | Path = DEFAULT_SAFE_COT) -> Dict[str, dict]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for row in rows:
        key = _norm_question(row.get("question", ""))
        if key:
            out[key] = row
    return out


def attach_safe_cot(rows: Sequence[dict], path: str | Path = DEFAULT_SAFE_COT) -> List[dict]:
    safe = load_safe_cot(path)
    out = []
    for row in rows:
        item = dict(row)
        match = safe.get(_norm_question(item.get("question", "")))
        if match:
            item["safe_cot"] = match.get("reasoned_idk_cot", "")
            item["safe_answer"] = match.get("reasoned_idk_answer", "")
        else:
            item["safe_cot"] = ""
            item["safe_answer"] = "I don't have sufficient information to answer that."
        out.append(item)
    return out


def load_forget_rows(
    path: str | Path,
    task_id: str = "1",
    safe_cot_file: str | Path = DEFAULT_SAFE_COT,
) -> List[dict]:
    rows = [r for r in read_jsonl(path)
            if str(r.get("task_id", "")) == str(task_id)]
    return attach_safe_cot(rows, safe_cot_file)


def split_dev(
    rows: Sequence[dict],
    dev_ratio: float = 0.10,
    seed: int = 1001,
) -> Tuple[List[dict], List[dict]]:
    rows = list(rows)
    random.Random(seed).shuffle(rows)
    n_dev = max(1, int(round(len(rows) * dev_ratio)))
    # never let dev swallow the whole set
    n_dev = min(n_dev, max(1, len(rows) - 1))
    return rows[n_dev:], rows[:n_dev]


def safe_target(row: dict, strategy: str) -> str:
    cot = (row.get("safe_cot") or "").strip()
    answer = (row.get("safe_answer") or "I don't know.").strip()
    if strategy == "DefaultCoT":
        cot = re.sub(r"</think>\s*$", "", cot).strip()
        return f"{cot}\n</think>\n\n{answer}" if cot else answer
    # The prompt already closed </think> for these strategies.
    return answer


def encode_example(tok, prompt: str, target: str, max_len: int):
    p_ids = tok(prompt, add_special_tokens=True)["input_ids"]
    t_ids = tok(target, add_special_tokens=False)["input_ids"] + [tok.eos_token_id]
    budget = max_len - len(t_ids)
    if budget <= 0:
        # safe-CoT can be long: keep the answer-bearing tail
        t_ids = t_ids[-(max_len - 1):]
        budget = max_len - len(t_ids)
    p_ids = p_ids[-budget:] if len(p_ids) > budget else p_ids
    ids = p_ids + t_ids
    return ids, [-100] * len(p_ids) + t_ids


def collate(tok, examples, max_len: int, device: str = "cuda"):
    ids, labels, mask = [], [], []
    for seq, lab in examples:
        pad = max_len - len(seq)
        if pad < 0:
            raise ValueError(f"example length {len(seq)} > max_len {max_len}")
        ids.append(seq + [tok.pad_token_id] * pad)
        labels.append(lab + [-100] * pad)
        mask.append([1] * len(seq) + [0] * pad)
    return (torch.tensor(ids, device=device),
            torch.tensor(labels, device=device),
            torch.tensor(mask, device=device))


def build_strategy_batches(
    tok,
    forget_rows: Sequence[dict],
    retain_rows: Sequence[dict],
    strategies: Sequence[str] = STRATEGY_ORDER,
    max_len: int = 512,
    device: str = "cuda",
) -> Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
    """One batch per strategy; forget uses safe CoT/answer, retain uses gold."""
    out = {}
    for strategy in strategies:
        examples = [
            encode_example(tok, build_prompt(r["question"], strategy),
                           safe_target(r, strategy), max_len)
            for r in forget_rows
        ]
        examples += [
            encode_example(tok, build_prompt(r["question"], strategy),
                           r["answer"], max_len)
            for r in retain_rows
        ]
        out[strategy] = collate(tok, examples, max_len, device=device)
    return out
