"""Leakage metrics. Ground truth is the dataset gold answer, never another model's output."""
from functools import lru_cache

from rouge_score import rouge_scorer

from data_utils import key_phrase

_ENTITY_THRESHOLD_ROUGE = 0.60


@lru_cache(maxsize=1)
def _scorer():
    return rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)


def rouge_l_recall(gold: str, response: str) -> float:
    if not gold or not response:
        return 0.0
    return float(_scorer().score(gold, response)["rougeL"].recall)


def entity_leak(gold: str, response: str) -> int:
    phrase = key_phrase(gold)
    if not phrase or not response:
        return 0
    return int(phrase.lower() in response.lower())


def score(gold: str, response: str) -> dict:
    r = rouge_l_recall(gold, response)
    e = entity_leak(gold, response)
    return {
        "key_phrase": key_phrase(gold),
        "entity_leak": e,
        "rougeL_recall": round(r, 6),
        "leak_any": int(e == 1 or r >= _ENTITY_THRESHOLD_ROUGE),
    }
