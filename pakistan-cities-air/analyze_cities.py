"""Compare one year of PM2.5 across six Pakistani cities against the WHO 2021 guideline.

Usage:
    python analyze_cities.py
Reads data/<city>_daily_pm25.csv, writes results/.
A city enters the full comparison only if it has enough data (see MIN_SENSORS, MIN_DAYS);
otherwise it is reported as "insufficient data", which is itself a finding.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from fetch_cities import CITIES  # noqa: E402

HERE = Path(__file__).parent
WHO_24H = 15.0  # µg/m³, WHO 2021 24-hour guideline (99th percentile, i.e. 3-4 exceedance days a year)
WHO_IT1_24H = 75.0  # µg/m³, WHO interim target 1
WHO_ANNUAL = 5.0  # µg/m³, WHO 2021 annual guideline
MIN_COVERAGE = 75.0  # % of hours in the day with data
MAX_PLAUSIBLE = 1000.0  # µg/m³
MIN_SENSORS = 3  # sensors with valid data over the year
MIN_DAYS = 300  # days with at least one valid sensor

INK, MUTED, GRID, ORANGE_LINE = "#0b0b0b", "#52514e", "#e6e5e0", "#52514e"
# Validated categorical slots 1-6, assigned in the fixed CITIES order
COLORS: Dict[str, str] = dict(zip(CITIES, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]))


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["pm25"] = pd.to_numeric(df["pm25"], errors="coerce")
    df = df.dropna(subset=["date", "pm25"])
    df = df[(df["pm25"] >= 0) & (df["pm25"] <= MAX_PLAUSIBLE)]
    if "coverage_pct" in df and df["coverage_pct"].notna().any():
        df = df[df["coverage_pct"].isna() | (df["coverage_pct"] >= MIN_COVERAGE)]
    return df.drop_duplicates(subset=["sensor_id", "date"])


def city_daily(df: pd.DataFrame) -> pd.DataFrame:
    """One value per day: the median across sensors reporting that day."""
    if df.empty:
        return pd.DataFrame(columns=["date", "pm25", "n_sensors"])
    return (df.groupby("date").agg(pm25=("pm25", "median"), n_sensors=("sensor_id", "nunique"))
              .reset_index().sort_values("date"))


def share_above(values: pd.Series, threshold: float) -> float:
    return float((values > threshold).mean()) if len(values) else float("nan")


def availability(city: str, raw: pd.DataFrame, cleaned: pd.DataFrame, daily: pd.DataFrame) -> Dict[str, object]:
    sensors_used = int(cleaned["sensor_id"].nunique())
    days = int(len(daily))
    return {
        "city": city,
        "sensors_found": int(raw["sensor_id"].nunique()) if not raw.empty else 0,
        "sensors_used": sensors_used,
        "reference_monitors": int(cleaned.loc[cleaned["is_monitor"] == True, "sensor_id"].nunique()),  # noqa: E712
        "days_with_data": days,
        "median_sensors_per_day": float(daily["n_sensors"].median()) if days else 0.0,
        "providers": ", ".join(sorted(cleaned["provider"].dropna().unique())) if not cleaned.empty else "",
        "included": sensors_used >= MIN_SENSORS and days >= MIN_DAYS,
    }


def summary(city: str, daily: pd.DataFrame) -> Dict[str, object]:
    worst = daily.loc[daily["pm25"].idxmax()]
    cleanest = daily.loc[daily["pm25"].idxmin()]
    mean = float(daily["pm25"].mean())
    return {
        "city": city,
        "days": int(len(daily)),
        "mean_pm25": round(mean, 1),
        "median_pm25": round(float(daily["pm25"].median()), 1),
        "mean_vs_who_annual_x": round(mean / WHO_ANNUAL, 1),
        "pct_days_above_15": round(100 * share_above(daily["pm25"], WHO_24H), 1),
        "days_at_or_below_15": int((daily["pm25"] <= WHO_24H).sum()),
        "pct_days_above_75": round(100 * share_above(daily["pm25"], WHO_IT1_24H), 1),
        "worst_day": worst["date"].date().isoformat(),
        "worst_pm25": round(float(worst["pm25"]), 1),
        "cleanest_day": cleanest["date"].date().isoformat(),
        "cleanest_pm25": round(float(cleanest["pm25"]), 1),
    }


def _style(ax: plt.Axes) -> None:
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def plot_monthly(monthly: pd.DataFrame, cities: List[str], out: Path) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 5.2), dpi=150)
    for city in cities:
        sub = monthly[monthly["city"] == city]
        ax.plot(sub["month"], sub["median_pm25"], color=COLORS[city], linewidth=2, marker="o", markersize=4, label=city)
        last = sub.iloc[-1]
        ax.annotate(city, (last["month"], last["median_pm25"]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=9, color=INK)
    ax.axhline(WHO_24H, color=ORANGE_LINE, linewidth=1.4, linestyle="--", label=f"WHO 24-hour guideline ({WHO_24H:g})")
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Monthly median PM2.5 (µg/m³)")
    ax.set_title("Monthly median PM2.5 by city", loc="left", fontsize=11, color=INK)
    ax.tick_params(axis="x", rotation=45)
    _style(ax)
    ax.legend(frameon=False, fontsize=8.5, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=7)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def plot_ranking(summ: pd.DataFrame, out: Path) -> None:
    s = summ.sort_values("mean_pm25")
    fig, ax = plt.subplots(figsize=(8, 0.6 * len(s) + 1.6), dpi=150)
    bars = ax.barh(s["city"], s["mean_pm25"], color=[COLORS[c] for c in s["city"]], height=0.6)
    for bar, mean, x in zip(bars, s["mean_pm25"], s["mean_vs_who_annual_x"]):
        ax.annotate(f"{mean:.0f} µg/m³  ({x:.0f}× WHO annual)", (bar.get_width(), bar.get_y() + bar.get_height() / 2),
                    xytext=(4, 0), textcoords="offset points", va="center", fontsize=9, color=INK)
    ax.axvline(WHO_ANNUAL, color=ORANGE_LINE, linewidth=1.4, linestyle="--")
    ax.set_xlim(0, s["mean_pm25"].max() * 1.45)
    ax.set_xlabel("Mean daily PM2.5 over the year (µg/m³); dashed line = WHO annual guideline (5)")
    ax.set_title("Yearly mean PM2.5 by city", loc="left", fontsize=11, color=INK)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    res = HERE / "results"
    res.mkdir(exist_ok=True)
    avail_rows, summ_rows, monthly_rows = [], [], []

    for city in CITIES:
        path = HERE / "data" / f"{city.lower()}_daily_pm25.csv"
        raw = pd.read_csv(path) if path.exists() else pd.DataFrame(columns=["sensor_id", "is_monitor", "provider"])
        cleaned = clean(raw) if not raw.empty else raw
        daily = city_daily(cleaned) if not raw.empty else city_daily(pd.DataFrame())
        avail = availability(city, raw, cleaned, daily)
        avail_rows.append(avail)
        if not avail["included"]:
            continue
        summ_rows.append(summary(city, daily))
        m = daily.assign(month=daily["date"].dt.to_period("M").astype(str))
        g = m.groupby("month").agg(days=("pm25", "size"), median_pm25=("pm25", "median"),
                                   pct_above_75=("pm25", lambda v: 100 * share_above(v, WHO_IT1_24H))).reset_index()
        monthly_rows.append(g.assign(city=city))

    avail_df = pd.DataFrame(avail_rows)
    avail_df.to_csv(res / "availability.csv", index=False)
    print("DATA AVAILABILITY\n" + avail_df.drop(columns=["providers"]).to_string(index=False))

    if not summ_rows:
        print("\nNo city has enough data for comparison.")
        return
    summ_df = pd.DataFrame(summ_rows).sort_values("mean_pm25", ascending=False)
    summ_df.to_csv(res / "city_summary.csv", index=False)
    monthly = pd.concat(monthly_rows, ignore_index=True).round(1)
    monthly.to_csv(res / "monthly_by_city.csv", index=False)
    included = [c for c in CITIES if c in set(summ_df["city"])]
    plot_monthly(monthly, included, res / "monthly_by_city.png")
    plot_ranking(summ_df, res / "yearly_mean_by_city.png")
    (res / "summary.json").write_text(json.dumps({"availability": avail_rows, "cities": summ_rows}, indent=2,
                                                 default=str), encoding="utf-8")
    cols = ["city", "days", "mean_pm25", "median_pm25", "mean_vs_who_annual_x", "pct_days_above_15",
            "days_at_or_below_15", "pct_days_above_75", "worst_day", "worst_pm25", "cleanest_day", "cleanest_pm25"]
    print("\nCOMPARISON (cities with enough data)\n" + summ_df[cols].to_string(index=False))


if __name__ == "__main__":
    main()
