"""Clean Lahore daily PM2.5, compare with the WHO 2021 guideline, and chart it.

Usage:
    python analyze.py
Reads data/raw_daily_pm25.csv, writes results/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).parent
WHO_24H = 15.0  # µg/m³, WHO 2021 24-hour guideline
WHO_IT1_24H = 75.0  # µg/m³, WHO interim target 1 (least strict)
WHO_ANNUAL = 5.0  # µg/m³, WHO 2021 annual guideline
MIN_COVERAGE = 75.0  # % of hours in the day with data
MAX_PLAUSIBLE = 1000.0  # µg/m³, above this treat as sensor error

INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
BLUE, ORANGE = "#2a78d6", "#eb6834"


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    """Drop impossible values and days with poor hourly coverage."""
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    df = df.dropna(subset=["date", "pm25"])
    df = df[(df["pm25"] >= 0) & (df["pm25"] <= MAX_PLAUSIBLE)]
    if "coverage_pct" in df and df["coverage_pct"].notna().any():
        df = df[df["coverage_pct"].isna() | (df["coverage_pct"] >= MIN_COVERAGE)]
    return df.drop_duplicates(subset=["sensor_id", "date"])


def city_daily(df: pd.DataFrame) -> pd.DataFrame:
    """One value per day: the median across all sensors reporting that day."""
    return (df.groupby("date")
              .agg(pm25=("pm25", "median"), n_sensors=("sensor_id", "nunique"))
              .reset_index()
              .sort_values("date"))


def exceedance(daily: pd.Series, threshold: float) -> float:
    """Share of days (0-1) above a threshold."""
    return float((daily > threshold).mean()) if len(daily) else float("nan")


def summarise(city: pd.DataFrame, clean_df: pd.DataFrame, raw: pd.DataFrame) -> Dict[str, object]:
    worst = city.loc[city["pm25"].idxmax()]
    return {
        "date_from": city["date"].min().date().isoformat(),
        "date_to": city["date"].max().date().isoformat(),
        "days_with_data": int(len(city)),
        "sensors_used": int(clean_df["sensor_id"].nunique()),
        "reference_monitors_used": int(clean_df.loc[clean_df["is_monitor"] == True, "sensor_id"].nunique()),  # noqa: E712
        "rows_raw": int(len(raw)),
        "rows_after_cleaning": int(len(clean_df)),
        "median_daily_pm25": round(float(city["pm25"].median()), 1),
        "mean_daily_pm25": round(float(city["pm25"].mean()), 1),
        "mean_vs_who_annual_x": round(float(city["pm25"].mean()) / WHO_ANNUAL, 1),
        "pct_days_above_who_24h": round(100 * exceedance(city["pm25"], WHO_24H), 1),
        "pct_days_above_who_it1_75": round(100 * exceedance(city["pm25"], WHO_IT1_24H), 1),
        "worst_day": worst["date"].date().isoformat(),
        "worst_day_pm25": round(float(worst["pm25"]), 1),
        "worst_day_vs_who_24h_x": round(float(worst["pm25"]) / WHO_24H, 1),
    }


def monthly(city: pd.DataFrame) -> pd.DataFrame:
    m = city.assign(month=city["date"].dt.to_period("M"))
    out = m.groupby("month").agg(
        days=("pm25", "size"),
        median_pm25=("pm25", "median"),
        pct_above_who=("pm25", lambda s: 100 * exceedance(s, WHO_24H)),
        pct_above_75=("pm25", lambda s: 100 * exceedance(s, WHO_IT1_24H)),
    ).reset_index()
    out["month"] = out["month"].astype(str)
    return out.round(1)


def _style(ax: plt.Axes) -> None:
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def plot_daily(city: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    ax.plot(city["date"], city["pm25"], color=BLUE, linewidth=1.6, label="Daily PM2.5 (median of sensors)")
    ax.axhline(WHO_24H, color=ORANGE, linewidth=1.6, linestyle="--", label=f"WHO 24-hour guideline ({WHO_24H:g} µg/m³)")
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.set_ylim(bottom=0)
    ax.set_title("Lahore daily PM2.5 vs the WHO guideline", loc="left", fontsize=11, color=INK)
    _style(ax)
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def plot_monthly(month_df: pd.DataFrame, out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=150)
    bars = ax.bar(month_df["month"], month_df["pct_above_who"], color=BLUE, width=0.7)
    for bar, v in zip(bars, month_df["pct_above_who"]):
        ax.annotate(f"{v:.0f}%", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    ha="center", va="bottom", fontsize=8, color=MUTED, xytext=(0, 2), textcoords="offset points")
    ax.set_ylim(0, 110)
    ax.set_ylabel("Days above WHO guideline (%)")
    ax.set_title("Share of days above 15 µg/m³, by month", loc="left", fontsize=11, color=INK)
    ax.tick_params(axis="x", rotation=45)
    _style(ax)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    raw = pd.read_csv(HERE / "data" / "raw_daily_pm25.csv")
    clean_df = clean(raw)
    city = city_daily(clean_df)
    res = HERE / "results"
    res.mkdir(exist_ok=True)

    summary = summarise(city, clean_df, raw)
    (res / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    month_df = monthly(city)
    month_df.to_csv(res / "monthly.csv", index=False)
    city.to_csv(res / "city_daily_pm25.csv", index=False)
    plot_daily(city, res / "daily_pm25.png")
    plot_monthly(month_df, res / "monthly_exceedance.png")

    print(json.dumps(summary, indent=2))
    print("\n" + month_df.to_string(index=False))


if __name__ == "__main__":
    main()
