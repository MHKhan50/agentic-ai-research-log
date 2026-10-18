"""Base-rate and human-review model for AI phone/seatbelt cameras.

The public trials report how many offences the AI *flagged*, but not how many flags were correct.
This model asks: for realistic ranges of offence prevalence and AI accuracy, how many flags are
wrong, how many wrong notices survive human review, and how much reviewer time the volumes need?

Every scenario value below is an assumption, labelled as such. The only measured inputs are the
public figures in data/public_figures.csv.

Usage:
    python camera_model.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).parent
RES = HERE / "results"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # validated categorical slots 1-4

# ---------------------------------------------------------------- scenario assumptions (not data)
# Offence prevalence comes from public estimates where available (see load_prevalence)
SENSITIVITY = 0.90  # share of real offences the AI flags
SPECIFICITY_GRID = [0.95 + i * 0.0005 for i in range(101)]  # 95.0% .. 100.0%
REVIEWER_FALSE_ACCEPT = [0.005, 0.01, 0.02, 0.05]  # share of wrong flags a reviewer still approves
SECONDS_PER_REVIEW = [15, 30, 60]


def precision(prevalence: float, sensitivity: float, specificity: float) -> float:
    """Share of AI flags that are real offences (positive predictive value)."""
    true_pos = sensitivity * prevalence
    false_pos = (1.0 - specificity) * (1.0 - prevalence)
    total = true_pos + false_pos
    return true_pos / total if total > 0 else float("nan")


def wrong_notices(flags: float, ai_precision: float, reviewer_false_accept: float) -> float:
    """Wrong flags that a human reviewer still approves, i.e. notices sent to innocent drivers."""
    return flags * (1.0 - ai_precision) * reviewer_false_accept


def review_hours(flags: float, seconds_per_review: float) -> float:
    return flags * seconds_per_review / 3600.0


def load_figures() -> Dict[str, float]:
    df = pd.read_csv(HERE / "data" / "public_figures.csv")
    out: Dict[str, float] = {}
    for r in df.itertuples():
        key = f"{r.source_id}.{r.metric}"
        out[key if key not in out else f"{key}.{r.period}"] = float(r.value)
    return out


def load_prevalence(fig: Dict[str, float]) -> Dict[str, float]:
    """Share of drivers offending, from public estimates (not assumptions)."""
    journeys = fig["scotland_2026.daily_vehicle_journeys"]
    return {
        "Scotland, seatbelt (est.)": fig["scotland_2026.drivers_not_wearing_seatbelt_daily"] / journeys,
        "NSW phone, 2019": 1.0 / fig["nsw.phone_use_one_in_n_drivers"],
        "Scotland, phone (est.)": fig["scotland_2026.drivers_using_handheld_phone_daily"] / journeys,
        "NSW phone, 2021": 1.0 / fig["nsw.phone_use_one_in_n_drivers.2021"],
    }


def _style(ax: plt.Axes) -> None:
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def plot_precision(prevalence: Dict[str, float], out: Path) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []
    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=150)
    for (name, prev), color in zip(prevalence.items(), SERIES):
        ys = [100 * precision(prev, SENSITIVITY, sp) for sp in SPECIFICITY_GRID]
        xs = [100 * sp for sp in SPECIFICITY_GRID]
        ax.plot(xs, ys, color=color, linewidth=2, label=f"{name}: {prev:.2%} of drivers")
        for sp in (0.99, 0.995, 0.999):
            rows.append({"scenario": name, "prevalence": round(prev, 5), "specificity": sp,
                         "sensitivity": SENSITIVITY, "precision": round(precision(prev, SENSITIVITY, sp), 4)})
    ax.set_xlim(95, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel("AI specificity: % of law-abiding drivers correctly NOT flagged")
    ax.set_ylabel("Share of flags that are real offences (%)")
    ax.set_title(f"How many AI flags are correct? (sensitivity fixed at {SENSITIVITY:.0%})", loc="left",
                 fontsize=11, color=INK)
    _style(ax)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return pd.DataFrame(rows)


def plot_wrong_notices(flags: float, out: Path) -> pd.DataFrame:
    precisions = [p / 100 for p in range(50, 100)]
    rows: List[Dict[str, float]] = []
    fig, ax = plt.subplots(figsize=(8.5, 4.6), dpi=150)
    for fa, color in zip(REVIEWER_FALSE_ACCEPT, SERIES):
        ys = [wrong_notices(flags, p, fa) for p in precisions]
        ax.plot([100 * p for p in precisions], ys, color=color, linewidth=2,
                label=f"reviewer approves {fa:.1%} of wrong flags")
        for p in (0.5, 0.8, 0.9, 0.95):
            rows.append({"flags": flags, "ai_precision": p, "reviewer_false_accept": fa,
                         "wrong_notices": round(wrong_notices(flags, p, fa), 1)})
    ax.set_xlabel("AI precision: share of flags that are real offences (%)")
    ax.set_ylabel("Wrong notices sent")
    ax.set_title(f"Wrong notices from {flags:,.0f} flags (West Midlands two-week volume)", loc="left",
                 fontsize=11, color=INK)
    _style(ax)
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return pd.DataFrame(rows)


def main() -> None:
    RES.mkdir(exist_ok=True)
    fig = load_figures()

    wm_flags = fig["wm_2026.seatbelt_flags"] + fig["wm_2026.phone_flags"]
    athens_valid_share = fig["athens_2026.judged_valid"] / fig["athens_2026.citations_human_reviewed"]
    athens_misread_share = fig["athens_2026.rejected_phone_seatbelt_misread"] / fig["athens_2026.citations_human_reviewed"]

    prevalence = load_prevalence(fig)
    precision_table = plot_precision(prevalence, RES / "precision_vs_specificity.png")
    notices_table = plot_wrong_notices(wm_flags, RES / "wrong_notices.png")
    workload = pd.DataFrame([{"flags": wm_flags, "seconds_per_review": s,
                              "review_hours": round(review_hours(wm_flags, s), 1),
                              "review_hours_per_week": round(review_hours(wm_flags, s) / 2, 1)}
                             for s in SECONDS_PER_REVIEW])

    precision_table.to_csv(RES / "precision_table.csv", index=False)
    notices_table.to_csv(RES / "wrong_notices_table.csv", index=False)
    workload.to_csv(RES / "review_workload.csv", index=False)

    summary = {
        "west_midlands_total_flags_2_weeks": int(wm_flags),
        "west_midlands_seatbelt_share_of_flags": round(fig["wm_2026.seatbelt_flags"] / wm_flags, 3),
        "west_midlands_flags_per_camera_site_per_day": round(wm_flags / 2 / 14, 1),
        "west_midlands_images_checked": int(fig["wm_2026.images_human_checked"]),
        "west_midlands_accuracy_published": False,
        "athens_share_of_reviewed_judged_valid": round(athens_valid_share, 3),
        "athens_share_of_reviewed_rejected_as_phone_seatbelt_misreads": round(athens_misread_share, 3),
        "prevalence_estimates": {k: round(v, 5) for k, v in prevalence.items()},
    }
    (RES / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("PUBLIC FIGURES -> DERIVED")
    print(json.dumps(summary, indent=2))
    print("\nPRECISION (share of flags that are real), sensitivity 90%")
    print(precision_table.pivot(index="scenario", columns="specificity", values="precision").to_string())
    print("\nWRONG NOTICES from West Midlands volume")
    print(notices_table.pivot(index="ai_precision", columns="reviewer_false_accept", values="wrong_notices").to_string())
    print("\nREVIEW WORKLOAD for West Midlands volume")
    print(workload.to_string(index=False))


if __name__ == "__main__":
    main()
