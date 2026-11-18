from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import analysis  # noqa: E402
import contradiction_judge as cj  # noqa: E402

CASES = {c["id"]: c for c in cj.bench.load_cases()}


def test_parse_three_labels() -> None:
    got = cj.parse_reply('ok {"1": "present", "2": "Contradicted", "3": "missing"}', 3, "three")
    assert got == {1: "present", 2: "contradicted", 3: "missing"}


def test_parse_rejects_unknown_or_incomplete() -> None:
    assert cj.parse_reply('{"1": "maybe"}', 1, "three") is None
    assert cj.parse_reply('{"1": "present"}', 2, "three") is None
    assert cj.parse_reply("no json", 1, "binary") is None
    assert cj.parse_reply("[1, 2]", 2, "binary") is None


def test_binary_parse_matches_earlier_rule() -> None:
    # as in ../llm-omission-judge/: anything that is not 'missing' counts as present
    assert cj.parse_reply('{"1": "contradicted", "2": "missing"}', 2, "binary") == {1: "present", 2: "missing"}


def test_binary_prompt_is_the_earlier_prompt() -> None:
    sys.path.insert(0, str(ROOT.parent / "llm-omission-judge"))
    import judge as old  # noqa: E402
    assert cj.SYSTEM["binary"] == old.JUDGE_PROMPT


def test_area_fact_added_once() -> None:
    c2 = cj.facts_for(CASES["C2"])  # already lists the side as a fact
    assert [f["id"] for f in c2].count("side") == 1 and "injured_area" not in [f["id"] for f in c2]
    c5 = cj.facts_for(CASES["C5"])
    assert c5[-1] == {"id": "injured_area", "text": "injured area: right ankle or foot", "critical": True}
    assert cj.facts_for(CASES["C1"])[-1]["text"] == "injured area: back"


def test_notes_are_200_with_unique_keys() -> None:
    notes = cj.load_notes()
    assert len(notes) == 200 and len({n["key"] for n in notes}) == 200


def test_area_reference() -> None:
    c5 = CASES["C5"]  # right ankle
    assert analysis.area_reference("Pain in the right ankle after a twist.", c5) == "present"
    assert analysis.area_reference("Pain in the left ankle after a twist.", c5) == "contradicted"
    assert analysis.area_reference("Pain in the right knee after a twist.", c5) == "contradicted"
    assert analysis.area_reference("Pain after a twist, daayen takhne mein.", c5) == "missing"


def test_stats() -> None:
    assert analysis.mcnemar_exact(0, 0) == 1.0
    assert analysis.mcnemar_exact(0, 6) == 0.0312
    lo, hi = analysis.wilson(5, 10)
    assert lo is not None and hi is not None and lo < 0.5 < hi


def fake_chat(model: str, system: str, user: str) -> str:
    """Scripted judge: binary says all present; three-label calls the injured area contradicted.
    The 'flaky' judge returns junk on the first try to exercise the retry."""
    if model == "flaky" and "JSON object only" not in user:
        return "Sorry, here is my answer"
    lines: List[str] = [x for x in user.split("Facts:\n")[1].splitlines() if x[:1].isdigit()]
    ans = {}
    for i, line in enumerate(lines, 1):
        area = "injured area" in line or line.split(". ", 1)[1].startswith("side:")
        ans[str(i)] = "contradicted" if ("contradicted" in system and area) else "present"
    return json.dumps(ans)


def test_end_to_end_offline_and_resume(tmp_path: Path) -> None:
    runs = tmp_path / "runs.jsonl"
    assert cj.main(chat=fake_chat, argv=["--judges", "fake", "flaky", "--limit", "6"], runs=runs) == 0
    recs = [json.loads(x) for x in runs.read_text(encoding="utf-8").splitlines()]
    assert len(recs) == 2 * 2 * 6 and all(r["parse_ok"] for r in recs)
    # a second start finds nothing left to do
    cj.main(chat=fake_chat, argv=["--judges", "fake", "flaky", "--limit", "6"], runs=runs)
    assert len(runs.read_text(encoding="utf-8").splitlines()) == 24

    out = analysis.main(argv=[], res=tmp_path, plot=False)
    rows = list(csv.DictReader((tmp_path / "area_fact.csv").open(encoding="utf-8")))
    assert len(rows) == 24
    assert all(r["judge_label"] == ("contradicted" if r["prompt"] == "three" else "present") for r in rows)
    paired = {(p["judge"], p["reference"]): p for p in out["paired_area_flags"]}
    for (judge, ref), p in paired.items():
        assert p["flagged_binary"] == 0 and p["flagged_three"] == p["paired_notes"]
    assert (tmp_path / "results.json").exists() and (tmp_path / "critical.csv").exists()


def test_failed_calls_are_retried_on_next_start(tmp_path: Path) -> None:
    runs = tmp_path / "runs.jsonl"

    def broken(model: str, system: str, user: str) -> str:
        raise TimeoutError("slow")

    assert cj.main(chat=broken, argv=["--judges", "fake", "--prompts", "three", "--limit", "2"], runs=runs) == 2
    assert cj.main(chat=fake_chat, argv=["--judges", "fake", "--prompts", "three", "--limit", "2"], runs=runs) == 0
    assert len(analysis.load_runs(runs)) == 2
