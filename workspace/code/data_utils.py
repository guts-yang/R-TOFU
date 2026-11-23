"""Dataset loading and sensitive-entity extraction. Ground truth always comes from the dataset."""
import json
import random
import re
from pathlib import Path

_CAP_PHRASE = re.compile(r"\b[A-Z][A-Za-z\-']+(?:\s+[A-Z][A-Za-z\-']+)+\b")
_STOP_PREFIX = {
    "the", "this", "that", "these", "those", "it", "its", "in", "on", "as", "at",
    "for", "from", "with", "according", "based", "a", "an", "i", "we", "you",
    "there", "here", "what", "who", "when", "where", "how", "let", "first",
    "second", "finally", "however", "also", "to", "of", "and", "but", "if",
}
_LEADING_TITLES = ("Author ", "Authors ", "The author ", "The Author ", "The ")


def read_jsonl(path) -> list:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sample_rows(path, n: int, seed: int, task_id=None) -> list:
    rows = read_jsonl(path)
    if task_id is not None:
        rows = [r for r in rows if str(r.get("task_id", "")) == str(task_id)]
    rng = random.Random(seed)
    rng.shuffle(rows)
    return rows[:n] if n > 0 else []


def _clean_phrase(phrase: str) -> str:
    phrase = phrase.strip()
    for title in _LEADING_TITLES:
        if phrase.startswith(title):
            phrase = phrase[len(title):]
            break
    phrase = re.sub(r"(?:'s|’s)$", "", phrase).strip()
    return phrase


def key_phrase(answer: str) -> str:
    """Longest capitalized multi-word phrase in the gold answer: the distinctive entity."""
    candidates = []
    for m in _CAP_PHRASE.finditer(answer or ""):
        phrase = _clean_phrase(m.group(0))
        if not phrase or " " not in phrase:
            continue
        first = phrase.split()[0].lower().strip("'")
        if first in _STOP_PREFIX:
            continue
        candidates.append(phrase)
    if not candidates:
        return ""
    def rank(p):
        return (len(p.split()), len(p))
    best = max(rank(p) for p in candidates)
    winners = [p for p in candidates if rank(p) == best]
    return winners[-1]


def refusals(path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip()]
