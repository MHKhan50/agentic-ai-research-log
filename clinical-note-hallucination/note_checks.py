"""Automatic checks on a drafted clinical note against its source transcript.

These checks do not decide what is a hallucination. They find omissions of
listed facts and flag note sentences that a clinician should review:
numbers or drug names that never appear in the transcript, and symptoms the
patient denied that the note mentions without a negation.
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Set

# "Subjective:", "**Plan**", "## Assessment", "S:" (single letters only with a colon)
HEADING_RE = re.compile(
    r"^\s*[#*\s]*(?:(subjective|objective|assessment|plan)\b\s*\**\s*[:\-]?|([SOAP])\s*\**\s*:)\s*\**\s*(.*)$",
    re.IGNORECASE,
)
SECTION_NAMES = {"s": "Subjective", "o": "Objective", "a": "Assessment", "p": "Plan"}
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
NEGATION_RE = re.compile(r"\b(no|not|denie[sd]|deny|without|negative|nil|absent|none)\b|n't\b", re.IGNORECASE)
DRUGS = (
    "ibuprofen", "paracetamol", "acetaminophen", "naproxen", "diclofenac", "codeine", "co-codamol",
    "tramadol", "morphine", "gabapentin", "pregabalin", "amitriptyline", "prednisolone", "aspirin",
    "omeprazole", "metformin", "amlodipine", "insulin", "steroid", "antibiotic", "muscle relaxant",
)


def split_sections(note: str) -> List[Dict[str, str]]:
    """Return [{'section', 'sentence'}] for every sentence of a SOAP note."""
    out: List[Dict[str, str]] = []
    current = "Other"
    for line in note.splitlines():
        if not line.strip():
            continue
        m = HEADING_RE.match(line)
        if m:
            key = (m.group(1) or m.group(2)).lower()
            current = SECTION_NAMES.get(key[0], "Other") if len(key) == 1 else key.capitalize()
            line = m.group(3)
            if not line.strip():
                continue
        text = re.sub(r"^\s*[-*•]\s*", "", line).strip()
        for sent in re.split(r"(?<=[.!?])\s+", text):
            sent = sent.strip(" *")
            if len(sent) > 2:
                out.append({"section": current, "sentence": sent})
    return out


def numbers_in(text: str) -> Set[str]:
    return {n.rstrip("0").rstrip(".") if "." in n else n for n in NUMBER_RE.findall(text)}


def missing_facts(note: str, facts: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    low = note.lower()
    return [f for f in facts if not re.search(str(f["pattern"]), low)]


def sentence_flags(sentence: str, transcript: str, denied: Sequence[Dict[str, str]]) -> List[str]:
    """Reasons a note sentence needs a clinician's review (empty list = no flag)."""
    flags: List[str] = []
    low, src = sentence.lower(), transcript.lower()
    extra_numbers = sorted(numbers_in(sentence) - numbers_in(transcript))
    if extra_numbers:
        flags.append("number not in transcript: " + ", ".join(extra_numbers))
    extra_drugs = [d for d in DRUGS if d in low and d not in src]
    if extra_drugs:
        flags.append("drug not in transcript: " + ", ".join(extra_drugs))
    if not NEGATION_RE.search(sentence):
        for d in denied:
            if re.search(d["pattern"], low):
                flags.append(f"denied '{d['text']}' stated without negation")
    return flags


def review_reason(section: str, flags: List[str]) -> Optional[str]:
    """Plan sentences are always reviewed: the CREOLA study found most major hallucinations there."""
    if flags:
        return "; ".join(flags)
    if section == "Plan":
        return "plan sentence"
    return None
