"""Summarise results/attempts.jsonl into a CSV table and one chart."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
LANG = {"en": "English", "ru": "Roman Urdu"}


def load(path: Path) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    runs: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        runs[(r["model"], r["lang"], r["task_id"])].append(r)
    return runs


def summarise(runs: Dict[Tuple[str, str, str], List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    groups: Dict[Tuple[str, str], List[List[Dict[str, Any]]]] = defaultdict(list)
    for (model, lang, _), attempts in runs.items():
        groups[(model, lang)].append(sorted(attempts, key=lambda a: a["attempt"]))
    table = []
    for (model, lang), items in sorted(groups.items()):
        n = len(items)
        first = [a[0] for a in items]
        last = [a[-1] for a in items]
        retried = [a for a in items if len(a) > 1]
        table.append({
            "model": model,
            "language": LANG[lang],
            "tasks": n,
            "strict_json_first_try": sum(r["strict_json"] for r in first),
            "schema_valid_first_try": sum(r["schema_valid"] for r in first),
            "schema_valid_after_feedback": sum(r["schema_valid"] for r in last),
            "value_correct_first_try": sum(r["value_correct"] for r in first),
            "value_correct_after_feedback": sum(r["value_correct"] for r in last),
            "tasks_needing_retry": len(retried),
            "schema_valid_but_value_wrong": sum(r["schema_valid"] and not r["value_correct"] for r in last),
        })
    return table


def plot(table: List[Dict[str, Any]], path: Path) -> None:
    labels = [f"{r['model']}\n{r['language']}" for r in table]
    first = [100 * r["value_correct_first_try"] / r["tasks"] for r in table]
    after = [100 * r["value_correct_after_feedback"] / r["tasks"] for r in table]
    x = range(len(table))
    w = 0.38
    fig, ax = plt.subplots(figsize=(2.6 + 1.9 * len(table), 4.6))
    b1 = ax.bar([i - w / 2 - 0.01 for i in x], first, w, color="#2a78d6", label="First try")
    b2 = ax.bar([i + w / 2 + 0.01 for i in x], after, w, color="#eb6834", label="After validator feedback")
    for bars in (b1, b2):
        ax.bar_label(bars, fmt="%.0f%%", padding=2, fontsize=9, color="#52514e")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Tool calls fully correct (%)")
    ax.set_title("Does validator feedback fix tool calls? (all values checked)", fontsize=11, loc="left")
    ax.legend(frameon=False, fontsize=9, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.yaxis.grid(True, color="#e6e5e1")
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight")


def main() -> None:
    table = summarise(load(RES / "attempts.jsonl"))
    with (RES / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    plot(table, RES / "self_correction.png")
    for r in table:
        print(r)
    print("\nSaved results/summary.csv and results/self_correction.png")


if __name__ == "__main__":
    main()
