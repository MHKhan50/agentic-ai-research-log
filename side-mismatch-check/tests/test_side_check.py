from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import side_check as sc  # noqa: E402

CASES = sc.load_cases()


def test_roman_urdu_side_words_map_to_english() -> None:
    assert sc.side_words("mera daayan ghutna") == {"right"}
    assert sc.side_words("baayen kandhe ke bal") == {"left"}
    assert sc.side_words("Seedhiyan chadhne se. Ultrasound normal.") == set()


def test_side_is_attached_to_the_body_part() -> None:
    assert ("left", "shoulder") in sc.side_parts("Mera baayan kandha 4 maheene se akra hua hai")
    assert ("right", "knee") in sc.side_parts("pain in the right knee for 5 days")
    assert ("right", "leg") in sc.side_parts("daayen taang mein pair tak dard")


def test_copied_roman_word_with_wrong_english_side_is_flagged() -> None:
    # C3 error seen before: "right shoulder (baayan ka...)" for a left shoulder.
    res = sc.run_checks(CASES["C3"]["ru"], "Pain in the right shoulder (baayan kandha) for 4 months.")
    assert not res["present"] and res["side_set"] and res["side_part"]


def test_missing_side_is_flagged_by_all_checks() -> None:
    res = sc.run_checks(CASES["C5"]["ru"], "Twisted ankle 2 days ago playing football.")
    assert res == {"present": True, "side_set": True, "side_part": True}


def test_correct_side_passes() -> None:
    res = sc.run_checks(CASES["C5"]["ru"], "Right ankle sprain, 2 days, football.")
    assert res == {"present": False, "side_set": False, "side_part": False}


def test_side_part_catches_side_swapped_between_body_parts() -> None:
    # C4: right shoulder spread and left neck turn are both said; a left shoulder is not.
    note = "Neck pain spreading to the left shoulder."
    res = sc.run_checks(CASES["C4"]["ru"], note)
    assert not res["side_set"] and res["side_part"]


def test_reference_uses_english_transcript() -> None:
    ref = sc.reference("Right ankle sprain.", CASES["C5"])
    assert not ref["ref_unsafe"]
    ref = sc.reference("Left ankle sprain.", CASES["C5"])
    assert ref["ref_wrong"] and ref["ref_unsafe"]


def test_two_hundred_notes_load() -> None:
    rows = sc.load_notes()
    assert len(rows) == 200
    assert sum(r["lang"] == "en" for r in rows) == 40
    assert all(r["case"] in CASES for r in rows)


def test_score_counts() -> None:
    rows = [
        {"ref_unsafe": True, "ref_wrong": True, "ref_unsupported": False, "ref_missing": False, "x": True},
        {"ref_unsafe": True, "ref_wrong": False, "ref_unsupported": False, "ref_missing": True, "x": False},
        {"ref_unsafe": False, "ref_wrong": False, "ref_unsupported": False, "ref_missing": False, "x": True},
    ]
    s = sc.score(rows, "x")
    assert (s["unsafe_caught"], s["unsafe"], s["safe_flagged"], s["catch_rate"]) == (1, 2, 1, 0.5)


def test_full_run_writes_outputs(tmp_path: Path) -> None:
    rows = sc.main([], out=tmp_path)
    assert len(rows) == 200
    for name in ("per_note.csv", "summary.csv", "to_label.csv", "catch_vs_false_flags.png"):
        assert (tmp_path / name).exists()
    assert sc.score_labels(tmp_path / "to_label.csv") is None  # nothing labelled yet
