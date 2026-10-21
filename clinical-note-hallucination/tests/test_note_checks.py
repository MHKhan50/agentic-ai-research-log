from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from note_checks import missing_facts, numbers_in, review_reason, sentence_flags, split_sections  # noqa: E402

NOTE = """**Subjective:**
- 3 weeks of low back pain, 6/10, worse in the morning.
**O:** Reflexes normal.
## Assessment
Muscle strain.
P: Start naproxen 500 mg. Review in 2 weeks."""
DENIED = [{"text": "numbness", "pattern": "numb"}]


def test_sections_are_split_into_sentences() -> None:
    rows = split_sections(NOTE)
    assert [r["section"] for r in rows] == ["Subjective", "Objective", "Assessment", "Plan", "Plan"]
    assert rows[-1]["sentence"] == "Review in 2 weeks."


def test_sentence_starting_with_article_a_is_not_a_heading() -> None:
    rows = split_sections("Subjective:\nA heavy box was lifted.")
    assert rows == [{"section": "Subjective", "sentence": "A heavy box was lifted."}]


def test_unsupported_number_and_drug_are_flagged() -> None:
    flags = sentence_flags("Start naproxen 500 mg.", "Ibuprofen 400 mg twice a day.", DENIED)
    assert any("500" in f for f in flags) and any("naproxen" in f for f in flags)
    assert numbers_in("1.0 g, 45.50 and 4") == {"1", "45.5", "4"}


def test_denied_symptom_needs_a_negation() -> None:
    assert sentence_flags("Reports numbness in both legs.", "", DENIED)
    assert sentence_flags("No numbness or saddle anaesthesia.", "", DENIED) == []
    assert sentence_flags("Patient denies numbness.", "", DENIED) == []


def test_plan_sentences_are_always_reviewed() -> None:
    assert review_reason("Plan", []) == "plan sentence"
    assert review_reason("Subjective", []) is None


def test_every_listed_fact_is_found_in_its_own_english_transcript() -> None:
    cases = json.loads((ROOT / "data" / "consultations.json").read_text(encoding="utf-8"))
    for case in cases:
        assert missing_facts(case["en"], case["facts"]) == [], case["id"]
        for d in case["denied"]:
            assert re.compile(d["pattern"])
