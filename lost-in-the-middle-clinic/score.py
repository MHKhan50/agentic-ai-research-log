"""Scoring: an answer is correct if any accepted keyword appears in it.

This follows the accuracy metric of Liu et al. (2023): does a correct answer
appear in the model output. Words match at a word start ("kandh" matches
"kandhe"); numbers match only as whole numbers ("34" does not match "340").
"""
from __future__ import annotations

import re
from typing import Iterable


def _pattern(keyword: str) -> str:
    kw = re.escape(keyword.lower())
    if keyword.isdigit():
        return r"(?<!\d)" + kw + r"(?!\d)"
    return r"(?<![a-z0-9])" + kw


def is_correct(answer: str, accept: Iterable[str]) -> bool:
    text = answer.lower()
    return any(re.search(_pattern(kw), text) for kw in accept)
