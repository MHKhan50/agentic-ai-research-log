from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from make_sheet import build  # noqa: E402
from score import kappa, score  # noqa: E402


def test_kappa_known_values() -> None:
    assert kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert kappa([True, True, False, False], [True, False, True, False]) == 0.0
    assert kappa([True, True], [True, True]) is None


def test_sheet_and_score_round_trip(tmp_path: Path) -> None:
    key = build(HERE.parent / "results" / "notes.jsonl", tmp_path)
    assert len(key) == 50
    assert sum(k["lang"] == "ru" for k in key) == 40
    assert len({k["note_id"] + k["model"] for k in key}) == 50

    # Fake reviewer who agrees with the automatic checks exactly.
    with (HERE.parent / "results" / "per_note.csv").open(encoding="utf-8") as fh:
        auto = {f"{r['case']}-{r['lang']}|{r['model']}": r for r in csv.DictReader(fh)}
    filled = tmp_path / "filled.csv"
    with filled.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["Code", "ref", "note", "a", "b", "c", "d", "Comment"])
        for k in key:
            r = auto[f"{k['note_id']}|{k['model']}"]
            yn = lambda b: "Y" if b else "N"  # noqa: E731
            w.writerow([k["code"], "", "",
                        yn(r["main_region_present"] == "False" or bool(r["unsupported_regions"])),
                        yn(r["side_present"] == "False" or r["wrong_side"] == "True"),
                        yn(int(r["critical_missing"]) > 0), "N", ""])
    res = score(filled, tmp_path / "review_key.csv", out=tmp_path)
    for r in res:
        if r["check"] in ("wrong_region", "side_problem", "missing_critical"):
            assert r["agreement"] == 1.0
    assert (tmp_path / "labels.csv").exists()
