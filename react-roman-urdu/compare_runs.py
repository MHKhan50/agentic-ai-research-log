"""Compare Run A (original names) with Run B (renamed entities, same questions and numbers).

Usage:
    python compare_runs.py
Writes results/name_swap_comparison.png and results/name_swap_comparison.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

HERE = Path(__file__).parent
RUNS = {
    "Run A: original names": HERE / "results/run-a-original-names/qwen2.5_3b/summary.csv",
    "Run B: renamed": HERE / "results/qwen2.5_3b/summary.csv",
}
COLORS = {"Run A: original names": "#2a78d6", "Run B: renamed": "#eb6834"}
CONDITIONS = [
    ("ReAct", "English"),
    ("ReAct", "Roman Urdu"),
    ("Direct (KB in prompt)", "English"),
    ("Direct (KB in prompt)", "Roman Urdu"),
]


def load() -> pd.DataFrame:
    frames = []
    for run, path in RUNS.items():
        df = pd.read_csv(path)
        df["run"] = run
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    df = load()
    table = df.pivot_table(index=["method", "language"], columns="run", values="accuracy").reindex(CONDITIONS)
    table["change_pp"] = (table["Run B: renamed"] - table["Run A: original names"]) * 100
    table.round(3).to_csv(HERE / "results/name_swap_comparison.csv")
    print(table.round(3).to_string())

    labels = [f"{m.split(' ')[0]}\n{lang}" for m, lang in CONDITIONS]
    fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=150)
    width = 0.36
    for i, run in enumerate(RUNS):
        xs = [x + (i - 0.5) * (width + 0.02) for x in range(len(CONDITIONS))]
        sub = df[df["run"] == run].set_index(["method", "language"]).reindex(CONDITIONS)
        bars = ax.bar(xs, sub["accuracy"] * 100, width, color=COLORS[run], label=run)
        for bar, ok, n in zip(bars, sub["n_correct"], sub["n"]):
            ax.annotate(f"{int(ok)}/{int(n)}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha="center", va="bottom", fontsize=9, color="#52514e",
                        xytext=(0, 2), textcoords="offset points")
    ax.set_xticks(range(len(CONDITIONS)), labels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title("Same questions, same numbers, different names (qwen2.5:3b)", loc="left", fontsize=11)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(HERE / "results/name_swap_comparison.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
