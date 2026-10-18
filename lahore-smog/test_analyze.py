"""Offline tests for the cleaning and exceedance logic (no API key needed)."""

from __future__ import annotations

import pandas as pd

from analyze import city_daily, clean, exceedance


def _raw() -> pd.DataFrame:
    return pd.DataFrame({
        "sensor_id": [1, 2, 1, 2, 1, 1],
        "is_monitor": [True, False, True, False, True, True],
        "date": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02", "2026-01-03", "2026-01-03"],
        "pm25": [100.0, 120.0, -5.0, 40.0, 5000.0, 10.0],
        "coverage_pct": [100, 90, 100, 50, 100, 100],
    })


def test_clean_drops_bad_values_and_low_coverage() -> None:
    df = clean(_raw())
    # -5 (negative), 5000 (implausible) and the 50% coverage day are removed;
    # the duplicate sensor/date keeps the first valid row
    assert sorted(df["pm25"].tolist()) == [10.0, 100.0, 120.0]


def test_city_daily_uses_median_across_sensors() -> None:
    city = city_daily(clean(_raw()))
    assert city["pm25"].tolist() == [110.0, 10.0]
    assert city["n_sensors"].tolist() == [2, 1]


def test_exceedance_share() -> None:
    assert exceedance(pd.Series([10.0, 20.0, 30.0, 15.0]), 15.0) == 0.5
