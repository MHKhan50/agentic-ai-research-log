from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import analysis  # noqa: E402
import records  # noqa: E402
import run  # noqa: E402
from score import is_correct  # noqa: E402


def test_twenty_facts_with_unique_ids() -> None:
    ids = [f["id"] for f in records.FACTS]
    assert len(ids) == 20 and len(set(ids)) == 20


def test_answer_appears_only_in_gold_note() -> None:
    for fact in records.FACTS:
        for lang in records.LANGS:
            for pos in records.POSITIONS:
                notes = records.build_notes(fact, lang, pos)
                assert len(notes) == records.N_NOTES
                hits = [i + 1 for i, n in enumerate(notes) if is_correct(n, fact["accept"])]
                assert hits == [pos], (fact["id"], lang, pos, hits)


def test_answer_not_in_question() -> None:
    for fact in records.FACTS:
        for lang in records.LANGS:
            assert not is_correct(records.question(fact, lang), fact["accept"]), fact["id"]


def test_distractors_identical_across_positions() -> None:
    fact = records.FACTS[3]
    for lang in records.LANGS:
        a = records.build_notes(fact, lang, 1)
        b = records.build_notes(fact, lang, records.N_NOTES)
        strip = lambda notes: [n.split(" ", 2)[2] for n in notes]  # drop "Visit n."
        assert strip(a[1:]) == strip(b[:-1])


def test_languages_are_parallel() -> None:
    fact = records.FACTS[0]
    en = records.build_notes(fact, "en", 15)
    ru = records.build_notes(fact, "ru", 15)
    assert [n.split(".")[0] for n in en] == [n.split(".")[0] for n in ru]
    assert "Dard" in ru[0] and "Pain" in en[0]


def test_scoring() -> None:
    assert is_correct("Diclofenac.", ["diclofenac"])
    assert is_correct("Daayen kandhe ka", ["shoulder", "kandh"])
    assert is_correct("34 weeks", ["34"])
    assert not is_correct("340 weeks", ["34"])
    assert not is_correct("Visit 3", ["34"])
    assert not is_correct("Not recorded", ["warfarin"])


def fake_chat(model: str, system: str, user: str) -> Tuple[str, Dict[str, object]]:
    """Scripted model: finds the fact only when the key note is first or last."""
    facts = {records.question(f, lang): f for f in records.FACTS for lang in records.LANGS}
    q = user.rsplit("Question: ", 1)[1].split("\n")[0]
    fact = facts[q]
    if "Visit notes" not in user:
        return "I do not know.", {"prompt_eval_count": 20, "eval_count": 4}
    notes = user.split("\n\nQuestion:")[0].split("\n\n")[1:]
    idx = [i for i, n in enumerate(notes) if is_correct(n, fact["accept"])][0]
    found = idx in (0, len(notes) - 1)
    answer = fact["accept"][0] if found else "Not in the notes."
    return answer, {"prompt_eval_count": 1500, "eval_count": 3}


def test_end_to_end_mock_run(tmp_path: Path) -> None:
    out = tmp_path / "runs.jsonl"
    n = run.main(["--models", "fake-a", "fake-b"], chat=fake_chat, out=out)
    expected = 2 * 2 * 20 * len(records.conditions())
    assert n == expected
    assert run.main(["--models", "fake-a", "fake-b"], chat=fake_chat, out=out) == 0  # resume skips all
    rows = [json.loads(l) for l in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == expected and not any(r["possibly_cut"] for r in rows)

    summary = analysis.main(runs=out, out_dir=tmp_path)
    en = summary["models"]["fake-a"]["en"]
    assert en["conditions"]["oracle"]["accuracy"] == 1.0
    assert en["conditions"]["closed_book"]["accuracy"] == 0.0
    assert en["conditions"]["pos01"]["accuracy"] == 1.0
    assert en["conditions"]["pos15"]["accuracy"] == 0.0
    assert en["best_minus_worst"] == 1.0
    assert en["first_vs_middle"]["only_first_correct"] == 20
    assert en["first_vs_middle"]["p_value"] < 0.001
    for name in ("results.json", "summary.csv", "position_curve.png"):
        assert (tmp_path / name).stat().st_size > 0


def test_mcnemar_no_difference() -> None:
    a = {"F01": True, "F02": False}
    assert analysis.mcnemar_exact(a, dict(a))["p_value"] == 1.0
