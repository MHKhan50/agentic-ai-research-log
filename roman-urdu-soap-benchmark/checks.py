"""Checks on a drafted SOAP note against its English source transcript.

Builds on ../translate-then-draft/body_checks.py with three changes found
while writing the larger case set:
- "back" no longer matches "come back" (it now needs "lower back", "back pain",
  "lumbar", "spine" and similar),
- the pelvis counts as hip/groin, and the heel and Achilles count as ankle/foot,
- a laterality check: the note must name the injured side and must not name
  the other side unless the transcript does.

The safety gate sends a note to a clinician when any check fails. It does not
decide that the note is wrong; it decides that a person must read it first.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

sys.path.append(str(Path(__file__).resolve().parent.parent / "clinical-note-hallucination"))
from note_checks import missing_facts  # noqa: E402

REGIONS: Dict[str, str] = {
    "back": r"\b(lower|low|upper|mid|middle)\s+back\b|\bback\s*(pain|ache|stiff)|backache|lumbar|thoracic|\bspin(e|al)\b",
    "neck": r"\bneck\b|cervical",
    "shoulder": r"\bshoulders?\b|rotator cuff",
    "knee": r"\bknees?\b|\bacl\b|patell",
    "hip/groin": r"\bhips?\b|\bgroin\b|pelvi",
    "ankle/foot": r"\bankles?\b|\bfoot\b|\bfeet\b|\bheels?\b|achilles|plantar",
    "wrist/hand": r"\bwrists?\b|\bhands?\b|\bfingers?\b|\bthumbs?\b|carpal|scaphoid",
    "elbow": r"\belbows?\b|epicondyl",
    "leg": r"\blegs?\b|thigh|\bcalf\b|\bcalves\b",
    "arm": r"\barms?\b",
    "head": r"\bhead\b|headache",
    "chest": r"\bchest\b",
}
SIDES = ("left", "right")


def regions_in(text: str) -> Set[str]:
    low = text.lower()
    return {name for name, pat in REGIONS.items() if re.search(pat, low)}


def sides_in(text: str) -> Set[str]:
    low = text.lower()
    return {s for s in SIDES if re.search(rf"\b{s}\b", low)}


def check_note(note: str, case: Dict[str, object]) -> Dict[str, object]:
    """All automatic checks for one note. `case` needs en, facts, main_region and side."""
    en = str(case["en"])
    found = regions_in(note)
    side: Optional[str] = case.get("side")  # type: ignore[assignment]
    note_sides, src_sides = sides_in(note), sides_in(en)
    missing = missing_facts(note, case["facts"])  # type: ignore[arg-type]
    res: Dict[str, object] = {
        "facts_listed": len(case["facts"]),  # type: ignore[arg-type]
        "facts_missing": len(missing),
        "critical_missing": sum(bool(f["critical"]) for f in missing),
        "missing_ids": "; ".join(str(f["id"]) for f in missing),
        "main_region_present": case["main_region"] in found,
        "unsupported_regions": "; ".join(sorted(found - regions_in(en))),
        "side_expected": side or "",
        "side_present": (side in note_sides) if side else "",
        "wrong_side": bool(side) and bool((note_sides - src_sides) - {side}),
    }
    res["gate_flag"] = gate(res)
    return res


def gate(res: Dict[str, object]) -> bool:
    """True when a clinician must read the note before it is used."""
    return bool(
        not res["main_region_present"]
        or res["unsupported_regions"]
        or res["side_present"] is False
        or res["wrong_side"]
        or int(res["critical_missing"]) > 0  # type: ignore[call-overload]
    )


def missing_by_fact(note: str, facts: Sequence[Dict[str, object]]) -> Dict[str, bool]:
    gone: List[str] = [str(f["id"]) for f in missing_facts(note, facts)]
    return {str(f["id"]): str(f["id"]) in gone for f in facts}
