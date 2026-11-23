"""Decoding strategies = reasoning-budget environments. Prompts follow R-TOFU's test.py template."""

STRATEGY_ORDER = ["DefaultCoT", "LessThink", "ZeroThink", "SummaryThink"]

_PREFIXES = {
    "DefaultCoT": "",
    "LessThink": "Okay, the user asked this, I can answer it without thinking much.\n",
    "ZeroThink": "\n",
    "SummaryThink": "Brief recap: the question asks for one specific biographical fact.\n",
}

DEFAULT_MAX_NEW_TOKENS = {
    "DefaultCoT": 512,
    "LessThink": 256,
    "ZeroThink": 256,
    "SummaryThink": 256,
}


def build_prompt(question: str, strategy: str) -> str:
    head = f"<｜User｜>{question}<｜Assistant｜>"
    if strategy == "DefaultCoT":
        return head + "<think>\n"
    if strategy not in _PREFIXES:
        raise ValueError(f"unknown strategy {strategy}; choose from {STRATEGY_ORDER}")
    return head + "<think>\n" + _PREFIXES[strategy] + "</think>\n\n"


def max_new_tokens(strategy: str, override: int = 0) -> int:
    return int(override) if override and override > 0 else DEFAULT_MAX_NEW_TOKENS[strategy]


def split_generation(text: str):
    """Return (cot, answer) from the model continuation. Prefilled strategies start in answer region."""
    if "</think>" in text:
        cot, _, answer = text.partition("</think>")
        return cot.strip(), answer.strip(), True
    return "", text.strip(), False
