"""Offline tests: no Ollama needed; the model is a scripted fake."""

from __future__ import annotations

import json

import pytest

import run
from agent import ClinicTools, direct, parse_step, react, safe_calculate, translate_then_react
from bench_items import FORMS, PATIENTS, THERAPISTS, build_items, build_kb
from scoring import extract_numbers, score


class Scripted:
    def __init__(self, turns):
        self.turns = iter(turns)

    def __call__(self, messages, stop=None):
        return next(self.turns)


def test_items_are_complete_and_paired():
    items = build_items()
    assert len(items) == 96 and len({i["id"] for i in items}) == 96
    for it in items:
        assert all(it[f] for f in FORMS)
    a = {i["base_id"]: i for i in items if i["name_set"] == "A"}
    b = {i["base_id"]: i for i in items if i["name_set"] == "B"}
    assert a.keys() == b.keys()
    for k in a:  # same numbers, different names
        if a[k]["gold"]["type"] == "number":
            assert a[k]["gold"] == b[k]["gold"]
        assert a[k]["en"] != b[k]["en"]


def test_gold_values():
    items = {i["id"]: i for i in build_items()}
    assert items["A01"]["gold"]["value"] == 6            # 10 - 4 sessions left
    assert items["A09"]["gold"]["value"] == 39           # 34 + 5 years
    assert items["A13"]["gold"]["value"] == 47           # 52 - 5 years ago
    assert items["A17"]["gold"]["value"] == 17           # 6 + 11 years of experience
    assert items["A24"]["gold"]["value"] == 5            # 6 is 5 fewer than 11
    assert items["A25"]["gold"]["value"] == 10           # 4 + 6 sessions done
    assert items["A41"]["gold"]["value"] == 4            # 10 - 4 - 2
    assert "saal baad" in items["A09"]["ru"] and "sal baad" in items["A09"]["ru_var"]


def test_kb_has_same_numbers_in_both_name_sets():
    ka, kb = build_kb("A"), build_kb("B")
    strip = lambda kb_: [{k: v for k, v in p.items() if k not in ("name", "therapist")} for p in kb_["patients"]]
    assert strip(ka) == strip(kb)
    assert len(ka["therapists"]) == len(THERAPISTS) and len(ka["patients"]) == len(PATIENTS)


def test_scoring():
    num = {"type": "number", "value": 6, "tol": 0.01}
    assert score("6 sessions", num) and score("chhe sessions", num)
    assert score("10 - 4 = 6", num, strict=True)
    assert score("6 sessions (10 - 4)", num) and not score("6 sessions (10 - 4)", num, strict=True)
    assert extract_numbers("do aur 3") == [3.0]
    days = {"type": "keywords", "groups": [["friday", "jumma"], ["saturday", "hafta"]]}
    assert score("Jumma aur Hafta", days) and not score("Friday only", days)
    choice = {"type": "choice", "answer": "ali", "other": "maryam"}
    assert score("Ali Khalid ne zyada kiye", choice)
    assert not score("Maryam ne Ali se zyada kiye", choice)
    assert not score("Khalid", choice)  # word boundary: 'ali' inside 'khalid' does not count


def test_calculator_and_parser():
    assert safe_calculate("(10 - 4) * 2") == 12
    with pytest.raises(ValueError):
        safe_calculate("__import__('os').system('ls')")
    assert parse_step("Thought: x\nAction: lookup_patient[Hina Aslam]")[1:] == ("lookup_patient", "Hina Aslam")


def test_react_loop_and_diagnostics():
    tools = ClinicTools(build_kb("A")).registry()
    llm = Scripted(["Thought: record\nAction: lookup_patient[Mudassar Munier]",
                    "Thought: saal baad\nAction: calculate[38 - 5]",
                    "Thought: done\nAction: Finish[33 saal]"])
    tr = react(llm, tools, "Mudassar Munier 5 saal baad kitne saal ke honge?")
    assert tr.answer == "33 saal" and tr.lookups == 1 and tr.calc_exprs == ["38 - 5"]
    assert run.op_error("+", tr.calc_exprs, correct=False)
    assert not run.op_error("+", ["38 + 5"], correct=False)


def test_translate_and_direct():
    tools = ClinicTools(build_kb("B")).registry()
    llm = Scripted(["How many sessions does Hina Aslam still have left?",
                    "Thought: done\nAction: Finish[6]"])
    tr = translate_then_react(llm, tools, "Hina Aslam ke kitne sessions abhi baqi hain?")
    assert tr.translation.startswith("How many") and tr.answer == "6"
    assert direct(Scripted(["6"]), build_kb("B"), "x").answer == "6"


def _fake_factory(model):
    def chat(messages, stop=None):
        if "Translate" in messages[0]["content"]:
            return messages[1]["content"]
        if stop:
            return "Thought: done\nAction: Finish[6]"
        return "6"
    return chat


def test_runner_end_to_end_and_resume(tmp_path):
    path = run.main(["--models", "fake-a", "fake-b", "--limit", "3", "--no-push"],
                    chat_factory=_fake_factory, out_dir=tmp_path)
    rows = [json.loads(line) for line in path.open()]
    assert len(rows) == 2 * 3 * (2 + 4 + 4)
    assert {r["method"] for r in rows} == {"direct", "react_en_shot", "react_ru_shot", "translate_react"}
    run.main(["--models", "fake-a", "fake-b", "--limit", "3", "--no-push"], chat_factory=_fake_factory,
             out_dir=tmp_path)
    assert len(path.read_text().splitlines()) == len(rows)  # nothing re-run

    import analysis
    res = analysis.main(path)
    assert res["calls"] == len(rows)
    assert (tmp_path / "tables.md").exists() and (tmp_path / "fig_accuracy.png").exists()
