from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import run  # noqa: E402
import summarise  # noqa: E402
from body_checks import region_errors, regions_in  # noqa: E402

EN = "Patient: I have had lower back pain for 3 weeks. No numbness in my legs."


def test_regions_are_found() -> None:
    assert regions_in("Pain in the lower back and both knees.") == {"back", "knee"}
    assert regions_in("Mild headaches, neck stiff.") == {"head", "neck"}


def test_wrong_body_part_is_flagged() -> None:
    res = region_errors("Patient reports pain in the knees.", EN, "back")
    assert res == {"main_region_present": False, "unsupported_regions": ["knee"]}


def test_correct_note_passes() -> None:
    res = region_errors("Low back pain for 3 weeks, legs normal.", EN, "back")
    assert res == {"main_region_present": True, "unsupported_regions": []}


def test_pipeline_runs_offline(tmp_path, monkeypatch) -> None:
    calls = []

    def fake_chat(model: str, system: str, user: str) -> str:
        calls.append(system[:9])
        if system.startswith("Translate"):
            return "Patient: lower back pain for 3 weeks."
        return "Subjective: Lower back pain for 3 weeks after lifting.\nPlan: Review in 2 weeks."

    monkeypatch.setattr(run, "RES", tmp_path)
    run.main(chat=fake_chat, argv=["--models", "fake"])
    notes = [json.loads(x) for x in (tmp_path / "notes.jsonl").read_text().splitlines()]
    assert len(notes) == 12 and calls.count("Translate") == 4
    monkeypatch.setattr(summarise, "RES", tmp_path)
    summarise.main()
    rows = list((tmp_path / "summary.csv").read_text().splitlines())
    assert len(rows) == 4 and (tmp_path / "translate_vs_direct.png").exists()
