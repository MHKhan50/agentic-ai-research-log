"""Combine automatic omissions with the manual labels in results/review.csv.

Labels in review.csv:
  label     ok | H   (H = hallucination: not supported by the transcript)
  severity  major | minor   (only for H; major = could change diagnosis or management)
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
LANGS = ("English", "Roman Urdu")


def read(name: str) -> List[Dict[str, str]]:
    with (RES / name).open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def summarise(omissions: List[Dict[str, str]], review: List[Dict[str, str]]) -> List[Dict[str, object]]:
    unlabelled = [r for r in review if r["label"].strip().lower() not in ("ok", "h")]
    if unlabelled:
        raise SystemExit(f"{len(unlabelled)} rows in results/review.csv still need a label (ok or H).")
    table = []
    for lang in LANGS:
        om = [r for r in omissions if r["language"] == lang]
        rv = [r for r in review if r["language"] == lang]
        hall = [r for r in rv if r["label"].strip().lower() == "h"]
        table.append({
            "language": lang,
            "notes": len({r["note_id"] for r in om}),
            "facts_listed": len(om),
            "facts_missing": sum(r["missing"] == "True" for r in om),
            "critical_facts_missing": sum(r["missing"] == "True" and r["critical"] == "True" for r in om),
            "sentences_reviewed": len(rv),
            "hallucinated_sentences": len(hall),
            "major_hallucinations": sum(r["severity"].strip().lower() == "major" for r in hall),
            "flagged_by_checker": sum(r["auto_flag"] != "plan sentence" for r in rv),
            "flagged_and_confirmed": sum(r["auto_flag"] != "plan sentence" for r in hall),
        })
    return table


def plot(table: List[Dict[str, object]], path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))
    colors = ["#2a78d6", "#eb6834"]
    panels = (("facts_missing", "Listed facts left out", "facts_listed"),
              ("hallucinated_sentences", "Unsupported sentences (labelled)", None))
    for ax, (key, title, denom) in zip(axes, panels):
        vals = [float(r[key]) for r in table]
        bars = ax.bar([r["language"] for r in table], vals, color=colors, width=0.55)
        labels = [f"{int(v)} / {r[denom]}" if denom else f"{int(v)}" for v, r in zip(vals, table)]
        ax.bar_label(bars, labels=labels, padding=2, fontsize=9, color="#52514e")
        ax.set_title(title, fontsize=11, loc="left")
        ax.set_ylim(0, max(vals + [1]) * 1.3)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.yaxis.grid(True, color="#e6e5e1")
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.suptitle("SOAP notes from a 3B local model: omissions and hallucinations", x=0.01, ha="left", fontsize=12)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")


def main() -> None:
    table = summarise(read("omissions.csv"), read("review.csv"))
    with (RES / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)
    plot(table, RES / "omissions_hallucinations.png")
    missed = defaultdict(list)
    for r in read("omissions.csv"):
        if r["missing"] == "True":
            missed[r["note_id"]].append(r["fact"] + ("*" if r["critical"] == "True" else ""))
    for r in table:
        print(r)
    print("\nMissing facts per note (* = critical):")
    for k in sorted(missed):
        print(f"  {k}: {', '.join(missed[k])}")
    print("\nSaved results/summary.csv and results/omissions_hallucinations.png")


if __name__ == "__main__":
    main()
