"""Answer scoring: numbers, keyword groups and two-way choices."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")

# Number words, used only when an answer contains no digits. Ambiguous Urdu words
# ("do" = two, "ek" = one) are left out because they are also common English/Urdu words.
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5, "chhe": 6, "chay": 6, "chhay": 6,
    "saat": 7, "aath": 8, "nau": 9, "das": 10, "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14,
    "pandrah": 15, "solah": 16, "satrah": 17, "atharah": 18, "unnees": 19, "bees": 20,
}


def extract_numbers(text: str) -> List[float]:
    nums = [float(x) for x in _NUM_RE.findall(text.replace(",", ""))]
    if nums:
        return nums
    words = re.findall(r"[a-z]+", text.lower())
    return [float(NUMBER_WORDS[w]) for w in words if w in NUMBER_WORDS]


def _word(name: str, text: str) -> Optional[int]:
    m = re.search(r"\b" + re.escape(name) + r"\b", text)
    return m.start() if m else None


def score(answer: Optional[str], gold: Dict[str, Any], strict: bool = False) -> bool:
    """Lenient: any number in the answer matches. Strict: the last number must match."""
    if not answer:
        return False
    if gold["type"] == "number":
        nums = extract_numbers(answer)
        if not nums:
            return False
        tol = float(gold.get("tol", 0.01))
        cands = nums[-1:] if strict else nums
        return any(abs(n - float(gold["value"])) <= tol for n in cands)
    text = answer.lower()
    if gold["type"] == "keywords":
        return all(any(alias in text for alias in group) for group in gold["groups"])
    if gold["type"] == "choice":
        win, lose = _word(gold["answer"], text), _word(gold["other"], text)
        if win is None:
            return False
        if strict:
            return lose is None
        return lose is None or win < lose
    raise ValueError(f"Unknown gold type: {gold['type']}")
