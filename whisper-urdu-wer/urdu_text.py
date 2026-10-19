"""Text normalisation for Urdu ASR evaluation.

Whisper and human references often differ in ways that are not real
recognition errors: Arabic vs Urdu code points for the same letter,
optional diacritics, punctuation, and digit styles. Both the reference
and the hypothesis go through the same function before scoring, so the
error rate counts word mistakes, not keyboard differences.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List

# Arabic code points that Urdu text often contains by mistake -> Urdu forms.
_CHAR_MAP: Dict[str, str] = {
    "ي": "ی",  # Arabic yeh -> Farsi/Urdu yeh
    "ى": "ی",  # alef maksura -> Urdu yeh
    "ك": "ک",  # Arabic kaf -> keheh
    "ه": "ہ",  # Arabic heh -> heh goal
    "‌": "",  # zero-width non-joiner
    "‍": "",  # zero-width joiner
    "‏": "",  # right-to-left mark
    "‎": "",  # left-to-right mark
}

# Arabic-Indic and extended (Urdu) digits -> ASCII digits.
for _i in range(10):
    _CHAR_MAP[chr(0x0660 + _i)] = str(_i)
    _CHAR_MAP[chr(0x06F0 + _i)] = str(_i)

_TRANSLATION = str.maketrans(_CHAR_MAP)

# Optional vowel marks (zabar, zer, pesh, tanween, shadd, jazm, etc.).
_DIACRITICS = re.compile("[ً-ْٖ-ٰٟ]")
_SPACES = re.compile(r"\s+")


def normalize_urdu(text: str) -> str:
    """Return a canonical form of Urdu (or mixed Urdu/English) text."""
    text = unicodedata.normalize("NFC", text)
    text = text.translate(_TRANSLATION)
    text = _DIACRITICS.sub("", text)
    cleaned: List[str] = []
    for ch in text:
        category = unicodedata.category(ch)
        # Drop punctuation and symbols, including Urdu full stop and comma.
        if category.startswith("P") or category.startswith("S"):
            cleaned.append(" ")
        else:
            cleaned.append(ch)
    text = "".join(cleaned).lower()
    return _SPACES.sub(" ", text).strip()


def words(text: str) -> List[str]:
    """Normalise and split into words."""
    normalised = normalize_urdu(text)
    return normalised.split(" ") if normalised else []
