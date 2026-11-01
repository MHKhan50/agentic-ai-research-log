from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import judge  # noqa: E402
import score  # noqa: E402


def test_parse_reply_accepts_json_inside_text() -> None:
    got = judge.parse_reply('Here: {"1": "present", "2": "Missing", "3": "present"}', 3)
    assert got == {1: False, 2: True, 3: False}


def test_parse_reply_rejects_incomplete_or_broken() -> None:
    assert judge.parse_reply('{"1": "present"}', 2) is None
    assert judge.parse_reply("no json here", 2) is None
    assert judge.parse_reply('{"1": present}', 1) is None


def test_kappa_edge_cases() -> None:
    assert score.cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert abs(score.cohen_kappa([True, False], [False, True]) + 1.0) < 1e-9


def fake_chat(model: str, system: str, user: str) -> str:
    # Says every fact is missing; the first call per note returns junk to exercise the retry.
    n = user.split("Facts:\n")[1].count("\n") + 1
    if "JSON object only" not in user and model == "flaky":
        return "sorry"
    return json.dumps({str(i): "missing" for i in range(1, n + 1)})


def test_end_to_end_offline(tmp_path: Path) -> None:
    judge.main(chat=fake_chat, argv=["--judges", "fake", "flaky", "--limit", "4"], out=tmp_path)
    rows = list(csv.DictReader((tmp_path / "judgements.csv").open(encoding="utf-8")))
    assert rows and all(r["parse_ok"] == "True" and r["judge_missing"] == "True" for r in rows)
    score.main(res=tmp_path, plot=False)
    agr = list(csv.DictReader((tmp_path / "agreement.csv").open(encoding="utf-8")))
    assert {a["judge"] for a in agr} == {"fake", "flaky"}
    dis = list(csv.DictReader((tmp_path / "disagreements.csv").open(encoding="utf-8")))
    # every fact the keywords found present is a disagreement with an all-missing judge
    assert len(dis) == sum(r["keyword_missing"] == "False" for r in rows)
