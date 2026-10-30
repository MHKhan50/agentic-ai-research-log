"""Summary table with 95% bootstrap intervals, paired English vs Roman Urdu test, and chart."""
from __future__ import annotations

import csv
import random
from math import comb
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
LANG_NAME = {"en": "English", "ru": "Roman Urdu"}


def read(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def is_true(v: str) -> bool:
    return str(v) == "True"


def bootstrap_ci(rows: Sequence[Dict[str, str]], n_boot: int = 2000, seed: int = 7) -> Tuple[float, float, float]:
    """Facts-missing rate with a 95% interval, resampling whole cases."""
    by_case: Dict[str, Tuple[int, int]] = {}
    for r in rows:
        m, n = by_case.get(r["case"], (0, 0))
        by_case[r["case"]] = (m + int(r["facts_missing"]), n + int(r["facts_listed"]))
    vals = list(by_case.values())
    rate = sum(m for m, _ in vals) / sum(n for _, n in vals)
    rng = random.Random(seed)
    boots = []
    for _ in range(n_boot):
        s = [rng.choice(vals) for _ in vals]
        boots.append(sum(m for m, _ in s) / sum(n for _, n in s))
    boots.sort()
    return rate, boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for b and c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def summarise(notes: List[Dict[str, str]]) -> List[Dict[str, object]]:
    table = []
    for model in sorted({r["model"] for r in notes}):
        for lang in ("en", "ru"):
            rows = [r for r in notes if r["model"] == model and r["lang"] == lang]
            if not rows:
                continue
            rate, lo, hi = bootstrap_ci(rows)
            sided = [r for r in rows if r["side_expected"]]
            table.append({
                "model": model, "language": LANG_NAME[lang], "notes": len(rows),
                "facts_missing": sum(int(r["facts_missing"]) for r in rows),
                "facts_listed": sum(int(r["facts_listed"]) for r in rows),
                "missing_pct": round(100 * rate, 1), "ci_low": round(100 * lo, 1), "ci_high": round(100 * hi, 1),
                "critical_missing": sum(int(r["critical_missing"]) for r in rows),
                "notes_wrong_or_missing_region": sum(not is_true(r["main_region_present"]) or bool(r["unsupported_regions"])
                                                     for r in rows),
                "notes_with_side": len(sided),
                "side_missing": sum(r["side_present"] == "False" for r in sided),
                "wrong_side": sum(is_true(r["wrong_side"]) for r in rows),
                "gate_flags": sum(is_true(r["gate_flag"]) for r in rows),
                "mean_seconds": round(sum(float(r["seconds"]) for r in rows) / len(rows), 1),
            })
    return table


def paired_tests(facts: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for model in sorted({r["model"] for r in facts}):
        for scope in ("all facts", "critical facts"):
            pairs: Dict[Tuple[str, str], Dict[str, bool]] = {}
            for r in facts:
                if r["model"] != model or (scope == "critical facts" and not is_true(r["critical"])):
                    continue
                pairs.setdefault((r["case"], r["fact"]), {})[r["lang"]] = is_true(r["missing"])
            full = [p for p in pairs.values() if len(p) == 2]
            b = sum(p["ru"] and not p["en"] for p in full)  # lost only in Roman Urdu
            c = sum(p["en"] and not p["ru"] for p in full)  # lost only in English
            out.append({"model": model, "scope": scope, "pairs": len(full), "missing_only_ru": b,
                        "missing_only_en": c, "mcnemar_p": round(mcnemar_exact(b, c), 4)})
    return out


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def chart(table: List[Dict[str, object]], path: Path) -> None:
    models = sorted({str(r["model"]) for r in table})
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.36
    for i, (lang, colour) in enumerate((("English", "#0E6E6E"), ("Roman Urdu", "#B8893B"))):
        rows = {str(r["model"]): r for r in table if r["language"] == lang}
        xs = [m + (i - 0.5) * width for m in range(len(models))]
        ys = [float(rows[m]["missing_pct"]) for m in models]
        err = [[ys[k] - float(rows[m]["ci_low"]) for k, m in enumerate(models)],
               [float(rows[m]["ci_high"]) - ys[k] for k, m in enumerate(models)]]
        ax.bar(xs, ys, width, yerr=err, capsize=4, label=lang, color=colour)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models)
    ax.set_ylabel("Listed facts missing from the note (%)")
    ax.set_title("20 physiotherapy consultations, 95% bootstrap intervals")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main(res: Path = RES) -> None:
    notes, facts = read(res / "per_note.csv"), read(res / "facts.csv")
    table, tests = summarise(notes), paired_tests(facts)
    write_csv(res / "summary.csv", table)
    write_csv(res / "paired_tests.csv", tests)
    chart(table, res / "facts_missing_by_language.png")
    for r in table:
        print(r)
    for t in tests:
        print(t)
    print("Saved results/summary.csv, results/paired_tests.csv, results/facts_missing_by_language.png")


if __name__ == "__main__":
    main()
