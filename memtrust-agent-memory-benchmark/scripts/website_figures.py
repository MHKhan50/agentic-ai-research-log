"""Website figure from outputs/summary.csv: attack success and correct clean memory, by policy.

    python scripts/website_figures.py --out figures_web
"""
import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
POLICIES = [("baseline_relevance", "Relevance only", "#C8102E"), ("provenance_filter", "Trust filter", "#1F4E9C"),
            ("provenance_plus_corroboration", "Trust + corroboration", "#5FA65A")]
RATES = [("0.1", "10% injected"), ("0.25", "25% injected")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="figures_web")
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    rows = {(r["poisoning_rate"], r["policy"]): r for r in csv.DictReader(open(ROOT / "outputs" / "summary.csv"))}
    fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.0))
    panels = [("attack_success_rate_on_poisoned", "Attack success (poisoned episodes)"),
              ("overall_task_success_rate", "Correct clean memory picked")]
    w = 0.26
    for ax, (metric, title) in zip(axes, panels):
        for i, (pol, label, colour) in enumerate(POLICIES):
            vals = [100 * float(rows[(rate, pol)][metric]) for rate, _ in RATES]
            bars = ax.bar([k + (i - 1) * w for k in range(len(RATES))], vals, w, color=colour, label=label)
            ax.bar_label(bars, fmt="%.1f%%", fontsize=7, padding=2, color="#333333")
        ax.set_xticks(range(len(RATES)), [n for _, n in RATES])
        ax.set_ylim(0, 110)
        ax.set_title(title, loc="left", fontsize=10)
        ax.grid(axis="y", color="#e6e5e1")
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[0].legend(frameon=False, fontsize=8, loc="upper right")
    fig.suptitle("Three memory rules in a synthetic simulator (no LLM)", x=0.01, ha="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(out / "memtrust-agent-memory.png", dpi=150)
    print("wrote", out / "memtrust-agent-memory.png")


if __name__ == "__main__":
    main()
