"""Answer scoring for the English vs Roman Urdu ReAct experiment."""

from __future__ import annotations

import re
from typing import Any

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def extract_numbers(text: str) -> list[float]:
    return [float(x) for x in _NUM_RE.findall(text.replace(",", ""))]


def score(answer: str | None, gold: dict[str, Any]) -> bool:
    """Lenient match.

    number   -> correct if ANY number in the answer is within ``tol`` of gold
    keywords -> every group must have at least one alias present (case-insensitive)
    """
    if not answer:
        return False
    if gold["type"] == "number":
        tol = float(gold.get("tol", 0.01))
        return any(abs(n - float(gold["value"])) <= tol for n in extract_numbers(answer))
    if gold["type"] == "keywords":
        text = answer.lower()
        return all(any(alias in text for alias in group) for group in gold["groups"])
    raise ValueError(f"Unknown gold type: {gold['type']}")
