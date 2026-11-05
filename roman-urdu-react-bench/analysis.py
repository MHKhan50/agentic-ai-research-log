"""Tables, intervals and figures from results/runs.jsonl (no model needed).

    python analysis.py            # writes results/results.json, results/tables.md and results/fig_*.png
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from bench_items import FORM_NAMES, TEMPLATES

HERE = Path(__file__).resolve().parent
N_BOOT, SEED = 2000, 20261105


def wilson(k: int, n: int, z: float = 1.96) -> List[float]:
    if n == 0:
        return [0.0, 0.0]
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0.0, c - h), min(1.0, c + h)]


def paired_diff(a: pd.Series, b: pd.Series, rng: np.random.Generator) -> Dict[str, Any]:
    """Mean of a - b over matched units, with a percentile bootstrap over units."""
    d = (a.astype(float) - b.astype(float)).dropna().to_numpy()
    if len(d) == 0:
        return {"diff": None, "ci95": [None, None], "n": 0}
    boots = rng.choice(d, size=(N_BOOT, len(d)), replace=True).mean(axis=1)
    return {"diff": float(d.mean()), "ci95": [float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))],
            "n": int(len(d))}


def load(path: Path) -> pd.DataFrame:
    df = pd.read_json(path, lines=True)
    return df.drop_duplicates(["model", "item_id", "form", "method"], keep="last")


def analyse(df: pd.DataFrame, out: Path) -> Dict[str, Any]:
    rng = np.random.default_rng(SEED)
    res: Dict[str, Any] = {"calls": int(len(df)), "models": sorted(df["model"].unique().tolist())}

    acc = (df.groupby(["model", "method", "form"])
             .agg(n=("correct", "size"), k=("correct", "sum"), k_strict=("correct_strict", "sum"),
                  op_error=("op_error", "mean"), skipped_lookup=("skipped_lookup", "mean"),
                  parse_error=("parse_errors", lambda s: float((s > 0).mean())),
                  max_steps=("hit_max_steps", "mean"), median_latency_s=("latency_s", "median"))
             .reset_index())
    acc["accuracy"] = acc["k"] / acc["n"]
    acc["accuracy_strict"] = acc["k_strict"] / acc["n"]
    acc["ci95"] = [wilson(int(k), int(n)) for k, n in zip(acc["k"], acc["n"])]
    res["accuracy"] = acc.to_dict(orient="records")

    contrasts: Dict[str, Any] = {}
    for model, g in df.groupby("model"):
        piv = g.pivot_table(index="item_id", columns=["method", "form"], values="correct", aggfunc="first")
        c: Dict[str, Any] = {}

        def col(method: str, form: str) -> Optional[pd.Series]:
            return piv[(method, form)] if (method, form) in piv.columns else None

        pairs = {
            "react_en_shot: Roman Urdu minus English": (("react_en_shot", "ru"), ("react_en_shot", "en")),
            "react_en_shot: chat spelling minus English": (("react_en_shot", "ru_var"), ("react_en_shot", "en")),
            "react_en_shot: chat spelling minus Roman Urdu": (("react_en_shot", "ru_var"), ("react_en_shot", "ru")),
            "direct: Roman Urdu minus English": (("direct", "ru"), ("direct", "en")),
            "English: ReAct minus direct": (("react_en_shot", "en"), ("direct", "en")),
            "Roman Urdu: ReAct minus direct": (("react_en_shot", "ru"), ("direct", "ru")),
            "Roman Urdu: Roman Urdu example minus English example": (("react_ru_shot", "ru"), ("react_en_shot", "ru")),
            "Roman Urdu: translate-then-ReAct minus ReAct": (("translate_react", "ru"), ("react_en_shot", "ru")),
            "Chat spelling: translate-then-ReAct minus ReAct": (("translate_react", "ru_var"),
                                                                ("react_en_shot", "ru_var")),
        }
        for name, (a, b) in pairs.items():
            ca, cb = col(*a), col(*b)
            if ca is not None and cb is not None:
                c[name] = paired_diff(ca, cb, rng)
        # Name swap: the same template instance with the other names (paired by base_id).
        r = g[g["method"] == "react_en_shot"]
        for form in ("en", "ru", "ru_var"):
            p = r[r["form"] == form].pivot_table(index="base_id", columns="name_set", values="correct", aggfunc="first")
            if {"A", "B"} <= set(p.columns):
                c[f"name set B minus A ({FORM_NAMES[form]})"] = paired_diff(p["B"], p["A"], rng)
        contrasts[model] = c
    res["contrasts"] = contrasts

    tmpl = (df[df["method"] == "react_en_shot"].groupby(["model", "template", "form"])["correct"]
              .mean().unstack("form").reset_index())
    res["by_template"] = tmpl.to_dict(orient="records")

    errs = df[(df["method"] != "direct") & (~df["correct"])]
    res["error_types"] = (errs.groupby(["model", "form"])
                             .agg(wrong=("correct", "size"), op_error=("op_error", "sum"),
                                  skipped_lookup=("skipped_lookup", "sum"), max_steps=("hit_max_steps", "sum"))
                             .reset_index().to_dict(orient="records"))

    (out / "results.json").write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    write_tables(acc, contrasts, out)
    figures(acc, tmpl, out)
    return res


def write_tables(acc: pd.DataFrame, contrasts: Dict[str, Any], out: Path) -> None:
    lines = ["# Results", "", "## Accuracy (lenient scoring, Wilson 95% CI)", "",
             "| Model | Method | Form | Correct | Accuracy | Strict | Op. error | Skipped lookup |",
             "|---|---|---|---|---|---|---|---|"]
    for r in acc.itertuples():
        lo, hi = r.ci95
        lines.append(f"| {r.model} | {r.method} | {FORM_NAMES[r.form]} | {int(r.k)}/{int(r.n)} | "
                     f"{100 * r.accuracy:.1f}% [{100 * lo:.1f}, {100 * hi:.1f}] | {100 * r.accuracy_strict:.1f}% | "
                     f"{100 * r.op_error:.1f}% | {100 * r.skipped_lookup:.1f}% |")
    lines += ["", "## Paired differences (percentage points, bootstrap 95% CI over items)", "",
              "| Model | Comparison | Difference | 95% CI | Items |", "|---|---|---|---|---|"]
    for model, cs in contrasts.items():
        for name, v in cs.items():
            if v["diff"] is None:
                continue
            lines.append(f"| {model} | {name} | {100 * v['diff']:+.1f} | "
                         f"[{100 * v['ci95'][0]:+.1f}, {100 * v['ci95'][1]:+.1f}] | {v['n']} |")
    (out / "tables.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def figures(acc: pd.DataFrame, tmpl: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colours = {"en": "#1f5f99", "ru": "#c0612b", "ru_var": "#e3a46b"}
    models = sorted(acc["model"].unique())
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, method in zip(axes, ("direct", "react_en_shot")):
        sub = acc[acc["method"] == method]
        for j, form in enumerate(("en", "ru", "ru_var")):
            xs, ys, err = [], [], [[], []]
            for i, m in enumerate(models):
                row = sub[(sub["model"] == m) & (sub["form"] == form)]
                if row.empty:
                    continue
                r = row.iloc[0]
                xs.append(i + (j - 1) * 0.26)
                ys.append(100 * r["accuracy"])
                err[0].append(100 * (r["accuracy"] - r["ci95"][0]))
                err[1].append(100 * (r["ci95"][1] - r["accuracy"]))
            ax.bar(xs, ys, 0.25, yerr=err, color=colours[form], label=FORM_NAMES[form], capsize=2)
        ax.set_xticks(range(len(models)))
        ax.set_xticklabels(models, fontsize=8)
        ax.set_title("Direct (database in prompt)" if method == "direct" else "ReAct (English example)", fontsize=10)
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("Accuracy (%)")
    axes[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out / "fig_accuracy.png", dpi=160)
    plt.close(fig)

    order = [t["id"] for t in TEMPLATES]
    for form in ("en", "ru"):
        if form not in tmpl.columns:
            return
    piv = tmpl.assign(gap=tmpl["en"] - tmpl["ru"]).pivot_table(index="template", columns="model", values="gap")
    piv = piv.reindex([t for t in order if t in piv.index])
    fig, ax = plt.subplots(figsize=(1.6 + 1.3 * len(piv.columns), 4.2))
    im = ax.imshow(100 * piv.to_numpy(dtype=float), cmap="RdBu_r", vmin=-100, vmax=100, aspect="auto")
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels(piv.columns, fontsize=8)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index, fontsize=8)
    for i in range(piv.shape[0]):
        for k in range(piv.shape[1]):
            v = piv.iat[i, k]
            if pd.notna(v):
                ax.text(k, i, f"{100 * v:+.0f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="English minus Roman Urdu (points)")
    ax.set_title("ReAct accuracy gap by question type", fontsize=10)
    fig.tight_layout()
    fig.savefig(out / "fig_template_gap.png", dpi=160)
    plt.close(fig)


def main(path: Optional[Path] = None) -> Dict[str, Any]:
    path = path or HERE / "results" / "runs.jsonl"
    if not path.exists():
        sys.exit(f"No results yet: {path}. Run python run.py first.")
    res = analyse(load(path), path.parent)
    print((path.parent / "tables.md").read_text(encoding="utf-8"))
    return res


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
