"""Summarise omissions and body-region errors per model and condition, and draw the chart."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
CONDITIONS = ("en-direct", "ru-direct", "ru-translate")


def read(name: str) -> List[Dict[str, str]]:
    with (RES / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def summarise(om: List[Dict[str, str]], body: List[Dict[str, str]],
              notes: List[Dict[str, object]]) -> List[Dict[str, object]]:
    table = []
    for model in sorted({r["model"] for r in om}):
        for cond in CONDITIONS:
            o = [r for r in om if r["model"] == model and r["condition"] == cond]
            b = [r for r in body if r["model"] == model and r["condition"] == cond]
            n = [r for r in notes if r["model"] == model and r["condition"] == cond]
            if not o:
                continue
            tr = [r for r in o if r["missing_in_translation"] != ""]
            table.append({
                "model": model, "condition": cond, "notes": len(b), "facts_listed": len(o),
                "facts_missing": sum(r["missing"] == "True" for r in o),
                "critical_missing": sum(r["missing"] == "True" and r["critical"] == "True" for r in o),
                "facts_missing_in_translation": sum(r["missing_in_translation"] == "True" for r in tr) if tr else "",
                "main_region_missing": sum(r["main_region_present"] == "False" for r in b),
                "notes_with_other_regions": sum(bool(r["unsupported_regions"]) for r in b),
                "mean_seconds": round(sum(float(r["seconds"]) for r in n) / max(len(n), 1), 1),
            })
    return table


def plot(table: List[Dict[str, object]], path: Path) -> None:
    models = sorted({str(r["model"]) for r in table})
    colors = {"en-direct": "#2a78d6", "ru-direct": "#eb6834", "ru-translate": "#1f9e75"}
    fig, ax = plt.subplots(figsize=(8, 3.8))
    width = 0.26
    for i, cond in enumerate(CONDITIONS):
        vals = [next((int(r["facts_missing"]) for r in table if r["model"] == m and r["condition"] == cond), 0)
                for m in models]
        xs = [k + (i - 1) * width for k in range(len(models))]
        bars = ax.bar(xs, vals, width, label=cond, color=colors[cond])
        ax.bar_label(bars, padding=2, fontsize=9, color="#52514e")
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models)
    ax.set_ylabel("Listed facts left out (of 42)")
    ax.yaxis.grid(True, color="#e6e5e1")
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=9)
    ax.set_title("Roman Urdu consultations: direct drafting vs translate-then-draft", loc="left", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")


def main() -> None:
    notes = [json.loads(line) for line in (RES / "notes.jsonl").read_text(encoding="utf-8").splitlines() if line]
    table = summarise(read("omissions.csv"), read("body_regions.csv"), notes)
    with (RES / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    plot(table, RES / "translate_vs_direct.png")
    for r in table:
        print(r)
    print("\nSaved results/summary.csv and results/translate_vs_direct.png")


if __name__ == "__main__":
    main()
