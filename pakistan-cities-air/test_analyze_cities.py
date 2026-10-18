"""Offline tests (no API key needed)."""

from __future__ import annotations

import pandas as pd

from analyze_cities import MIN_DAYS, availability, city_daily, clean, share_above, summary


def _raw(n_days: int, n_sensors: int) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=n_days).strftime("%Y-%m-%d")
    rows = [{"sensor_id": s, "is_monitor": False, "provider": "P", "date": d, "pm25": 20.0 + s, "coverage_pct": 100}
            for s in range(n_sensors) for d in dates]
    return pd.DataFrame(rows)


def test_city_needs_enough_sensors_and_days() -> None:
    raw = _raw(MIN_DAYS, 3)
    c = clean(raw)
    assert availability("A", raw, c, city_daily(c))["included"] is True
    small = _raw(MIN_DAYS, 2)
    c2 = clean(small)
    assert availability("B", small, c2, city_daily(c2))["included"] is False


def test_clean_drops_negative_and_low_coverage() -> None:
    raw = pd.DataFrame({"sensor_id": [1, 1, 1], "is_monitor": [False] * 3, "provider": ["P"] * 3,
                        "date": ["2026-01-01", "2026-01-02", "2026-01-03"],
                        "pm25": [-1.0, 30.0, 40.0], "coverage_pct": [100, 100, 10]})
    assert clean(raw)["pm25"].tolist() == [30.0]


def test_summary_counts_clean_days() -> None:
    daily = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]),
                          "pm25": [10.0, 15.0, 80.0, 20.0], "n_sensors": [3] * 4})
    s = summary("A", daily)
    assert s["days_at_or_below_15"] == 2
    assert s["pct_days_above_75"] == 25.0
    assert share_above(daily["pm25"], 15.0) == 0.5
