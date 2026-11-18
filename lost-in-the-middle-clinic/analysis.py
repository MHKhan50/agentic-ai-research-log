"""Tables, chart and statistics from results/runs.jsonl (no model needed).

For each model and language:
- accuracy at each gold-note position, closed book and oracle, with 95%
  bootstrap intervals over the 20 facts (2,000 resamples, seed 42)
- best minus worst position (the robustness gap Liu et al. 2023 propose)
- paired tests (exact McNemar on the facts that differ):
  middle (pos15) vs first (pos01), and English vs Roman Urdu at each position

Writes results/summary.csv, results/results.json and results/position_curve.png,
and prints a Markdown table for the README.
"""
from __future__ import annotations

import csv
import json
import random
from math import comb
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import records

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
POS_CONDS = [f"pos{p:02d}" for p in records.POSITIONS]
LANG_NAME = {"en": "English", "ru": "Roman Urdu"}
COLOURS = {"en": "#2b5ce6", "ru": "#d62828"}  # blue, red
CLOSED_COLOUR = "#e9b10a"  # yellow
ORACLE_COLOUR = "#3fae5a"  # green

Table = Dict[Tuple[str, str, str], Dict[str, bool]]  # (model, lang, cond) -> fact -> correct


def load(path: Path) -> Table:
    table: Table = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                r = json.loads(line)
                table.setdefault((r["model"], r["lang"], r["condition"]), {})[r["fact"]] = bool(r["correct"])
    return table


def bootstrap_ci(values: Sequence[bool], n: int = 2000, seed: int = 42) -> Tuple[float, float]:
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    k = len(values)
    means = sorted(sum(values[rng.randrange(k)] for _ in range(k)) / k for _ in range(n))
    return (means[int(0.025 * n)], means[int(0.975 * n) - 1])


def mcnemar_exact(a: Dict[str, bool], b: Dict[str, bool]) -> Dict[str, object]:
    """Two-sided exact McNemar test over the facts both sides have."""
    shared = sorted(set(a) & set(b))
    only_a = sum(1 for f in shared if a[f] and not b[f])
    only_b = sum(1 for f in shared if b[f] and not a[f])
    n = only_a + only_b
    p = 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(only_a, only_b) + 1)) / 2 ** n)
    return {"n_pairs": len(shared), "only_first_correct": only_a, "only_second_correct": only_b,
            "p_value": round(p, 4)}


def summarise(table: Table) -> Dict[str, object]:
    models = sorted({m for m, _, _ in table})
    out: Dict[str, object] = {"models": {}, "n_facts": len(records.FACTS),
                              "positions": list(records.POSITIONS), "n_notes": records.N_NOTES}
    for m in models:
        mres: Dict[str, object] = {}
        for lang in records.LANGS:
            rows: Dict[str, object] = {}
            for cond in records.conditions():
                vals = list(table.get((m, lang, cond), {}).values())
                if not vals:
                    continue
                lo, hi = bootstrap_ci(vals)
                rows[cond] = {"correct": sum(vals), "n": len(vals),
                              "accuracy": round(sum(vals) / len(vals), 4),
                              "ci95": [round(lo, 4), round(hi, 4)]}
            pos_acc = [rows[c]["accuracy"] for c in POS_CONDS if c in rows]  # type: ignore[index]
            summary: Dict[str, object] = {"conditions": rows}
            if pos_acc:
                summary["best_minus_worst"] = round(max(pos_acc) - min(pos_acc), 4)
            first, mid = table.get((m, lang, "pos01")), table.get((m, lang, "pos15"))
            if first and mid:
                summary["first_vs_middle"] = mcnemar_exact(first, mid)
            mres[lang] = summary
        mres["en_vs_ru"] = {c: mcnemar_exact(table[(m, "en", c)], table[(m, "ru", c)])
                            for c in records.conditions()
                            if (m, "en", c) in table and (m, "ru", c) in table}
        out["models"][m] = mres  # type: ignore[index]
    return out


def write_csv(summary: Dict[str, object], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["model", "language", "condition", "correct", "n", "accuracy", "ci95_low", "ci95_high"])
        for m, mres in summary["models"].items():  # type: ignore[union-attr]
            for lang in records.LANGS:
                for cond, r in mres.get(lang, {}).get("conditions", {}).items():
                    w.writerow([m, LANG_NAME[lang], cond, r["correct"], r["n"], r["accuracy"], *r["ci95"]])


def markdown(summary: Dict[str, object]) -> str:
    head = ["Model", "Language", "Closed book", "Oracle"] + [f"Note {p}" for p in records.POSITIONS] + ["Best - worst"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for m, mres in summary["models"].items():  # type: ignore[union-attr]
        for lang in records.LANGS:
            s = mres.get(lang)
            if not s:
                continue
            conds = s["conditions"]
            cells = [f"{conds[c]['correct']}/{conds[c]['n']}" if c in conds else "-"
                     for c in ["closed_book", "oracle"] + POS_CONDS]
            gap = s.get("best_minus_worst")
            lines.append("| " + " | ".join([m, LANG_NAME[lang]] + cells +
                                           [f"{gap * 100:.0f} pts" if gap is not None else "-"]) + " |")
    return "\n".join(lines)


def plot(summary: Dict[str, object], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    models = list(summary["models"])  # type: ignore[arg-type]
    fig, axes = plt.subplots(1, len(models), figsize=(5.2 * len(models), 4.2), sharey=True, squeeze=False)
    for ax, m in zip(axes[0], models):
        mres = summary["models"][m]  # type: ignore[index]
        for lang in records.LANGS:
            conds = mres.get(lang, {}).get("conditions", {})
            xs = [p for p, c in zip(records.POSITIONS, POS_CONDS) if c in conds]
            ys = [conds[c]["accuracy"] * 100 for c in POS_CONDS if c in conds]
            lo = [conds[c]["ci95"][0] * 100 for c in POS_CONDS if c in conds]
            hi = [conds[c]["ci95"][1] * 100 for c in POS_CONDS if c in conds]
            ax.plot(xs, ys, marker="o", color=COLOURS[lang], label=LANG_NAME[lang])
            ax.fill_between(xs, lo, hi, color=COLOURS[lang], alpha=0.12)
            for cond, colour, style in (("closed_book", CLOSED_COLOUR, "--"), ("oracle", ORACLE_COLOUR, ":")):
                if cond in conds:
                    ax.axhline(conds[cond]["accuracy"] * 100, color=colour, linestyle=style, linewidth=1.2)
        ax.set_title(m)
        ax.set_xlabel(f"Position of the key note (of {records.N_NOTES})")
        ax.set_xticks(list(records.POSITIONS))
        ax.set_ylim(-3, 103)
        ax.grid(alpha=0.25)
    axes[0][0].set_ylabel("Correct answers (%)")
    handles, labels = axes[0][0].get_legend_handles_labels()
    from matplotlib.lines import Line2D
    handles += [Line2D([], [], color=CLOSED_COLOUR, linestyle="--"), Line2D([], [], color=ORACLE_COLOUR, linestyle=":")]
    labels += ["Closed book (no notes)", "Oracle (key note only)"]
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=9)
    fig.suptitle("Where the key fact sits in a 30-visit record", fontsize=12)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(runs: Optional[Path] = None, out_dir: Path = RES) -> Dict[str, object]:
    runs = runs or out_dir / "runs.jsonl"
    table = load(runs)
    summary = summarise(table)
    cut = sum(1 for line in runs.open(encoding="utf-8") if line.strip() and json.loads(line).get("possibly_cut"))
    summary["prompts_possibly_cut"] = cut
    (out_dir / "results.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(summary, out_dir / "summary.csv")
    plot(summary, out_dir / "position_curve.png")
    print(markdown(summary))
    print()
    for m, mres in summary["models"].items():  # type: ignore[union-attr]
        for lang in records.LANGS:
            t = mres.get(lang, {}).get("first_vs_middle")
            if t:
                print(f"{m} {LANG_NAME[lang]}: note 1 vs note 15, only note 1 right {t['only_first_correct']}, "
                      f"only note 15 right {t['only_second_correct']}, p = {t['p_value']}")
        for c, t in mres["en_vs_ru"].items():
            if c.startswith("pos"):
                print(f"{m} {c}: only English right {t['only_first_correct']}, "
                      f"only Roman Urdu right {t['only_second_correct']}, p = {t['p_value']}")
    print(f"\nPrompts possibly cut by the context limit: {cut}")
    print(f"Wrote {out_dir / 'results.json'}, summary.csv and position_curve.png")
    return summary


if __name__ == "__main__":
    main()
