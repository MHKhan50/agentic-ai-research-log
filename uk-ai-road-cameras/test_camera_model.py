"""Offline tests for the model maths."""

from __future__ import annotations

import math

from camera_model import precision, review_hours, wrong_notices


def test_precision_matches_hand_calculation() -> None:
    # 1% offend, AI catches 90%, wrongly flags 1% of the rest:
    # true = 0.9 * 0.01 = 0.009, false = 0.01 * 0.99 = 0.0099 -> 0.009 / 0.0189
    assert math.isclose(precision(0.01, 0.90, 0.99), 0.009 / 0.0189)


def test_perfect_specificity_means_every_flag_is_real() -> None:
    assert precision(0.01, 0.90, 1.0) == 1.0


def test_wrong_notices_and_workload() -> None:
    assert math.isclose(wrong_notices(10_000, 0.9, 0.01), 10.0)
    assert review_hours(3600, 30) == 30.0
