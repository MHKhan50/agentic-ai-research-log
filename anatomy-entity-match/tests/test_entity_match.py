from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import entity_match as em  # noqa: E402

CASES = em.sc.load_cases()


def fake_encoder(xs: Sequence[str]) -> np.ndarray:
    """Letter-count vectors: offline stand-in for BioLORD."""
    out = np.zeros((len(xs), 26))
    for i, x in enumerate(xs):
        for ch in x.lower():
            if "a" <= ch <= "z":
                out[i, ord(ch) - 97] += 1
    return out


def test_anatomy_reads_sides_in_both_languages() -> None:
    assert em.anatomy("I twisted my right ankle") == {"right ankle"}
    assert em.anatomy("mera daayan takhna mur gaya") == {"right ankle"}
    assert em.anatomy("lower back pain, no fever") == {"lower back"}


def test_soft_score_identity_and_empty() -> None:
    assert abs(em.soft_score({"right knee"}, {"right knee"}, fake_encoder) - 1.0) < 1e-9
    assert em.soft_score(set(), set(), fake_encoder) == 1.0
    assert em.soft_score({"knee"}, set(), fake_encoder) == 0.0


def test_swaps() -> None:
    assert em.swap_sides("Right knee, left side") == "Left knee, right side"
    assert em.swap_part("pain in the right knee", "knee") == "pain in the right ankle"
    assert em.swap_part("no body part here", "knee") is None


def test_code_check_catches_side_and_part_errors() -> None:
    en = CASES["C5"]["en"]  # right ankle sprain
    assert not em.code_check(en, "Right ankle sprain, swollen on the outside.")
    assert em.code_check(en, "Left ankle sprain.")
    assert em.code_check(en, "Right knee LCL sprain.")


def test_label_marks_known_errors() -> None:
    case = CASES["C5"]
    assert not em.label("Right ankle sprain after football.", case)["unsafe"]
    assert em.label("Right knee sprain after football.", case)["part_unsafe"]


def test_auroc() -> None:
    assert em.auroc([0.1, 0.2], [0.9, 0.8]) == 1.0
    assert em.auroc([0.5], [0.5]) == 0.5


def test_full_run_offline(tmp_path: Path) -> None:
    stats = em.main([], enc=fake_encoder, out=tmp_path)
    assert stats["notes"] == 200
    assert (tmp_path / "summary.csv").exists() and (tmp_path / "soft_vs_code.png").exists()
