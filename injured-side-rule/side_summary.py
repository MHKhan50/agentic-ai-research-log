"""Summary table, paired tests against the baseline, and a chart."""
from __future__ import annotations

import csv
from math import comb
from pathlib import Path
from typing import Dict, List

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
ORDER = ("baseline", "rule", "rule_glossary", "retry")


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value (same as roman-urdu-soap-benchmark)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def read(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def t(v: str) -> bool:
    return str(v) == "True"


def table(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    out = []
    for model in sorted({r["model"] for r in rows}):
        for cond in ORDER:
            g = [r for r in rows if r["model"] == model and r["condition"] == cond]
            if not g:
                continue
            sided = [r for r in g if r["side_expected"]]
            out.append({
                "model": model, "condition": cond, "notes": len(g),
                "side_present": sum(t(r["side_present"]) for r in sided), "sided_cases": len(sided),
                "wrong_side": sum(t(r["wrong_side"]) for r in sided),
                "unsupported_side_any_case": sum(t(r["unsupported_side"]) for r in g),
                "facts_missing": sum(int(r["facts_missing"]) for r in g),
                "facts_listed": sum(int(r["facts_listed"]) for r in g),
                "critical_missing": sum(int(r["critical_missing"]) for r in g),
                "region_wrong_or_missing": sum((not t(r["main_region_present"])) or bool(r["unsupported_regions"])
                                               for r in g),
                "retried": sum(t(r["retried"]) for r in g),
                "cut_at_cap": sum(t(r.get("cut_at_cap", "")) for r in g),
                "marked_incomplete": sum(t(r["marked_incomplete"]) for r in g),
                "gate_flags": sum(t(r["gate_flag"]) for r in g),
                "mean_seconds": round(sum(float(r["seconds"]) for r in g) / len(g), 1),
            })
    return out


def paired(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    """Exact McNemar on 'side present', each condition vs baseline, same model and case."""
    out = []
    idx = {(r["model"], r["condition"], r["case"]): r for r in rows if r["side_expected"]}
    for model in sorted({r["model"] for r in rows}):
        for cond in ORDER[1:]:
            keys = [k for k in idx if k[0] == model and k[1] == cond and (model, "baseline", k[2]) in idx]
            if not keys:
                continue
            fixed = sum(t(idx[k]["side_present"]) and not t(idx[(model, "baseline", k[2])]["side_present"]) for k in keys)
            broke = sum(not t(idx[k]["side_present"]) and t(idx[(model, "baseline", k[2])]["side_present"]) for k in keys)
            out.append({"model": model, "condition": cond, "cases": len(keys), "side_fixed": fixed,
                        "side_lost": broke, "p_mcnemar": round(mcnemar_exact(fixed, broke), 4)})
    return out


def write(path: Path, rows: List[Dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def chart(tab: List[Dict[str, object]], path: Path) -> None:
    models = sorted({str(r["model"]) for r in tab})
    conds = [c for c in ORDER if any(r["condition"] == c for r in tab)]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    width = 0.8 / max(1, len(models))
    colours = ["#1f6f8b", "#e07a1f", "#6a8d2f"]
    for i, m in enumerate(models):
        vals = []
        for c in conds:
            r = next((r for r in tab if r["model"] == m and r["condition"] == c), None)
            vals.append(100 * int(r["side_present"]) / max(1, int(r["sided_cases"])) if r else 0)
        xs = [j + (i - (len(models) - 1) / 2) * width for j in range(len(conds))]
        ax.bar(xs, vals, width, label=m, color=colours[i % len(colours)])
    ax.set_xticks(range(len(conds)))
    ax.set_xticklabels([c.replace("_", " + ") for c in conds])
    ax.set_ylabel("Roman Urdu notes naming the injured side (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(res: Path = RES) -> None:
    rows = read(res / "per_note.csv")
    tab = table(rows)
    write(res / "summary.csv", tab)
    pt = paired(rows)
    if pt:
        write(res / "paired_tests.csv", pt)
    chart(tab, res / "side_present_by_condition.png")
    for r in tab:
        print(f"{r['model']:12s} {r['condition']:13s} side {r['side_present']}/{r['sided_cases']}"
              f"  wrong {r['wrong_side']}  unsupported(any) {r['unsupported_side_any_case']}"
              f"  facts {r['facts_missing']}/{r['facts_listed']}  critical {r['critical_missing']}"
              f"  retried {r['retried']}  cut {r['cut_at_cap']}  incomplete {r['marked_incomplete']}  gate {r['gate_flags']}")
    for r in pt:
        print(f"{r['model']:12s} {r['condition']:13s} fixed {r['side_fixed']} lost {r['side_lost']} p={r['p_mcnemar']}")


if __name__ == "__main__":
    main()
