"""Body-region checks for drafted notes.

The main error in the Roman Urdu notes of clinical-note-hallucination/ was a
wrong body part (lower back became knees, knee became groin). This module
flags it automatically: a note should name the consultation's main region,
and should not name a body region that never appears in the English
transcript of the same consultation.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

REGIONS: Dict[str, str] = {
    "back": r"\b(lower |low )?back\b|lumbar|spine|spinal",
    "neck": r"\bneck\b|cervical",
    "shoulder": r"\bshoulders?\b",
    "knee": r"\bknees?\b",
    "hip/groin": r"\bhips?\b|\bgroin\b",
    "ankle/foot": r"\bankles?\b|\bfoot\b|\bfeet\b",
    "wrist/hand": r"\bwrists?\b|\bhands?\b|\bfingers?\b",
    "elbow": r"\belbows?\b",
    "leg": r"\blegs?\b|thigh|calf",
    "arm": r"\barms?\b",
    "head": r"\bhead\b|headache",
    "chest": r"\bchest\b",
}


def regions_in(text: str) -> Set[str]:
    low = text.lower()
    return {name for name, pat in REGIONS.items() if re.search(pat, low)}


def region_errors(note: str, english_transcript: str, main_region: str) -> Dict[str, object]:
    """Return the main-region check and any regions the source never mentions."""
    found = regions_in(note)
    extra: List[str] = sorted(found - regions_in(english_transcript))
    return {"main_region_present": main_region in found, "unsupported_regions": extra}
