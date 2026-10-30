from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run  # noqa: E402
import summarise  # noqa: E402
from checks import check_note, regions_in  # noqa: E402

CASES = run.load_cases()


def test_twenty_cases_with_both_languages() -> None:
    assert len(CASES) == 20
    assert len({c["id"] for c in CASES}) == 20
    for c in CASES:
        assert c["en"] and c["ru"] and c["facts"]


def test_every_fact_and_region_is_in_its_english_transcript() -> None:
    for c in CASES:
        en = c["en"].lower()
        for f in c["facts"]:
            assert re.search(f["pattern"], en), (c["id"], f["id"])
        assert c["main_region"] in regions_in(c["en"]), c["id"]
        if c["side"]:
            assert re.search(rf"\b{c['side']}\b", en), c["id"]


def test_come_back_is_not_the_back() -> None:
    assert "back" not in regions_in("Come back in 2 weeks.")
    assert "back" in regions_in("Lower back pain for 3 weeks.")


def test_faithful_note_passes_gate() -> None:
    case = next(c for c in CASES if c["id"] == "C5")
    res = check_note(case["en"], case)
    assert res["facts_missing"] == 0 and res["gate_flag"] is False


def test_wrong_side_and_wrong_region_are_flagged() -> None:
    case = next(c for c in CASES if c["id"] == "C5")
    res = check_note("Left knee pain after football. Paracetamol. Sprain.", case)
    assert res["wrong_side"] is True
    assert res["main_region_present"] is False
    assert res["unsupported_regions"] == "knee"
    assert res["gate_flag"] is True


def test_mcnemar() -> None:
    assert summarise.mcnemar_exact(0, 0) == 1.0
    assert summarise.mcnemar_exact(10, 0) < 0.01


def test_pipeline_with_fake_model(tmp_path: Path) -> None:
    def fake(model: str, system: str, user: str) -> str:
        return user  # echo the transcript: an English echo keeps every fact
    run.main(chat=fake, argv=["--models", "fake", "--cases", "C5", "C11"], out=tmp_path)
    notes = summarise.read(tmp_path / "per_note.csv")
    assert len(notes) == 4
    en = [r for r in notes if r["lang"] == "en"]
    assert all(r["facts_missing"] == "0" for r in en)
    summarise.main(res=tmp_path)
    tests = json.dumps(summarise.read(tmp_path / "paired_tests.csv"))
    assert "fake" in tests
    assert (tmp_path / "facts_missing_by_language.png").exists()
