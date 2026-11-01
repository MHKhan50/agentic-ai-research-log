from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import side_rule  # noqa: E402
import side_summary as summarise  # noqa: E402

CASES = {c["id"]: c for c in side_rule.bench.load_cases()}


def test_trigger_finds_every_case_with_an_injured_side() -> None:
    for c in CASES.values():
        if c["side"]:
            assert side_rule.transcript_has_side(c["ru"]), c["id"]


def test_trigger_ignores_seedhi_and_ultrasound() -> None:
    assert not side_rule.transcript_has_side("Seedhiyan chadhne se dard. Ultrasound normal.")


def test_baseline_has_all_forty_roman_urdu_notes() -> None:
    base = side_rule.load_baseline()
    assert len(base) == 40
    assert all(k[1] in CASES for k in base)


def test_unsupported_side_is_caught() -> None:
    c5 = CASES["C5"]  # right ankle
    assert side_rule.side_checks("Left ankle sprain.", c5)["unsupported_side"] is True
    assert side_rule.side_checks("Right ankle sprain.", c5)["unsupported_side"] is False


def test_pipeline_with_fake_model(tmp_path: Path) -> None:
    calls = []

    def fake(model: str, system: str, user: str) -> str:
        calls.append(user)
        if "Draft note:" in user:
            return "Right ankle sprain after football."
        return "Ankle sprain after football."

    baseline = tmp_path / "base.jsonl"
    baseline.write_text(
        '{"model": "fake", "case": "C5", "lang": "ru", "seconds": 1.0, "note": "Ankle sprain."}\n'
        '{"model": "fake", "case": "C1", "lang": "ru", "seconds": 1.0, "note": "Back pain."}\n',
        encoding="utf-8")
    side_rule.main(chat=fake, argv=["--models", "fake", "--cases", "C1", "C5"], out=tmp_path,
                   baseline_path=baseline)
    rows = summarise.read(tmp_path / "per_note.csv")
    assert len(rows) == 8
    retry = {r["case"]: r for r in rows if r["condition"] == "retry"}
    assert retry["C5"]["retried"] == "True" and retry["C5"]["side_present"] == "True"
    assert retry["C1"]["retried"] == "False"  # no side word in C1, so no retry
    rule = next(r for r in rows if r["condition"] == "rule" and r["case"] == "C5")
    assert rule["marked_incomplete"] == "True"
    summarise.main(res=tmp_path)
    pt = summarise.read(tmp_path / "paired_tests.csv")
    assert any(r["condition"] == "retry" and r["side_fixed"] == "1" for r in pt)
    assert (tmp_path / "side_present_by_condition.png").exists()


def test_resume_skips_saved_notes_and_retries_a_timeout(tmp_path: Path) -> None:
    baseline = tmp_path / "base.jsonl"
    baseline.write_text('{"model": "fake", "case": "C5", "lang": "ru", "seconds": 1.0, "note": "Right ankle."}\n',
                        encoding="utf-8")
    side_rule.time.sleep = lambda s: None  # type: ignore[assignment]
    state = {"calls": 0}

    def flaky(model: str, system: str, user: str) -> str:
        state["calls"] += 1
        if state["calls"] == 1:
            raise TimeoutError("stalled")
        return "Right ankle sprain."

    argv = ["--models", "fake", "--cases", "C5", "--conditions", "rule", "rule_glossary"]
    side_rule.main(chat=flaky, argv=argv, out=tmp_path, baseline_path=baseline)
    assert state["calls"] == 3  # one timeout, then two notes
    side_rule.main(chat=flaky, argv=argv, out=tmp_path, baseline_path=baseline)
    assert state["calls"] == 3  # nothing drafted again
    assert len(summarise.read(tmp_path / "per_note.csv")) == 2
