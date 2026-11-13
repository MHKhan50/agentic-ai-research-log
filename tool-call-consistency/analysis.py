"""Analyse results/runs.jsonl (no model needed).

Writes results/summary.csv, results/task_outcomes.csv, results/results.json
and results/pass_k.png.
"""
from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from consistency import HERE, N_TRIALS, canonical_output, pass_hat_k  # noqa: E402

LANG = {"en": "English", "ru": "Roman Urdu"}
COND = {"wording": "Five wordings, temperature 0", "sampling": "Same wording, temperature 0.7, 5 seeds"}
COLOURS = {("en", 0): "#1F4E9C", ("ru", 0): "#C8102E", ("en", 1): "#E3A800", ("ru", 1): "#7CB342"}
N_BOOT = 2000

Group = Tuple[str, str, str]  # model, lang, condition


def load(path: Path) -> Dict[Group, Dict[str, List[Dict[str, Any]]]]:
    groups: Dict[Group, Dict[str, List[Dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    seen = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r["key"] in seen:
            continue
        seen.add(r["key"])
        groups[(r["model"], r["lang"], r["condition"])][r["task_id"]].append(r)
    return groups


def mean_pass_k(counts: List[int], k: int) -> float:
    return sum(pass_hat_k(N_TRIALS, c, k) for c in counts) / len(counts)


def bootstrap_ci(counts: List[int], k: int, rng: random.Random) -> Tuple[float, float]:
    stats = sorted(mean_pass_k([rng.choice(counts) for _ in counts], k) for _ in range(N_BOOT))
    return stats[int(0.025 * N_BOOT)], stats[int(0.975 * N_BOOT) - 1]


def summarise(groups: Dict[Group, Dict[str, List[Dict[str, Any]]]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rng = random.Random(42)
    summary, outcomes = [], []
    for (model, lang, cond), by_task in sorted(groups.items()):
        complete = {t: rows for t, rows in by_task.items() if len(rows) == N_TRIALS}
        if not complete:
            continue
        counts = [sum(r["passed"] for r in rows) for rows in complete.values()]
        distinct = [len({canonical_output(r["parsed"]) for r in rows}) for rows in complete.values()]
        row: Dict[str, Any] = {"model": model, "language": LANG[lang], "condition": cond,
                               "tasks": len(counts), "trials_per_task": N_TRIALS}
        for k in (1, 3, 5):
            lo, hi = bootstrap_ci(counts, k, rng)
            row[f"pass^{k}"] = round(mean_pass_k(counts, k), 3)
            row[f"pass^{k}_ci"] = [round(lo, 3), round(hi, 3)]
        row["always_pass"] = sum(c == N_TRIALS for c in counts)
        row["never_pass"] = sum(c == 0 for c in counts)
        row["mixed"] = sum(0 < c < N_TRIALS for c in counts)
        row["mean_distinct_outputs"] = round(sum(distinct) / len(distinct), 2)
        row["curve"] = [round(mean_pass_k(counts, k), 3) for k in range(1, N_TRIALS + 1)]
        summary.append(row)
        for task_id, rows in sorted(complete.items()):
            errs = Counter(e for r in rows for e in r["value_errors"])
            outcomes.append({"model": model, "language": LANG[lang], "condition": cond,
                             "task_id": task_id, "passed_of_5": sum(r["passed"] for r in rows),
                             "distinct_outputs": len({canonical_output(r["parsed"]) for r in rows}),
                             "wrong_keys": ";".join(f"{k}x{v}" for k, v in sorted(errs.items())),
                             "failed_trials": ";".join(str(r["trial"]) for r in sorted(rows, key=lambda x: x["trial"]) if not r["passed"])})
    return summary, outcomes


def plot(summary: List[Dict[str, Any]], path: Path) -> None:
    models = sorted({r["model"] for r in summary})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)
    ks = list(range(1, N_TRIALS + 1))
    for ax, cond in zip(axes, ("wording", "sampling")):
        for r in summary:
            if r["condition"] != cond:
                continue
            lang = "en" if r["language"] == "English" else "ru"
            mi = models.index(r["model"]) % 2
            ax.plot(ks, [100 * v for v in r["curve"]], marker="o", lw=2,
                    ls="-" if lang == "en" else "--", color=COLOURS[(lang, mi)],
                    label=f"{r['model']}, {r['language']}")
        ax.set_title(COND[cond], fontsize=10, loc="left")
        ax.set_xticks(ks)
        ax.set_xlabel("k (all k tries must be fully correct)")
        ax.set_ylim(0, 105)
        ax.yaxis.grid(True, color="#e6e5e1")
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_ylabel("pass^k (%)")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=9)
    fig.suptitle("Clinic tool calls: does the model get it right every time?", x=0.06, ha="left", fontsize=12)
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main(results_dir: Path = HERE / "results") -> List[Dict[str, Any]]:
    summary, outcomes = summarise(load(results_dir / "runs.jsonl"))
    if not summary:
        raise SystemExit("No complete groups in runs.jsonl yet.")
    flat = [{k: (f"{v[0]}-{v[1]}" if isinstance(v, list) and k.endswith("_ci") else v)
             for k, v in r.items() if k != "curve"} for r in summary]
    with (results_dir / "summary.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flat[0]))
        w.writeheader()
        w.writerows(flat)
    with (results_dir / "task_outcomes.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(outcomes[0]))
        w.writeheader()
        w.writerows(outcomes)
    (results_dir / "results.json").write_text(json.dumps({"summary": summary, "task_outcomes": outcomes},
                                                         indent=2, ensure_ascii=False), encoding="utf-8")
    plot(summary, results_dir / "pass_k.png")
    print(f"{'model':13s} {'language':11s} {'condition':9s} pass^1  pass^5 [95% CI]      always/mixed/never  distinct")
    for r in summary:
        lo, hi = r["pass^5_ci"]
        print(f"{r['model']:13s} {r['language']:11s} {r['condition']:9s} {r['pass^1']:.2f}   "
              f"{r['pass^5']:.2f} [{lo:.2f}-{hi:.2f}]    {r['always_pass']}/{r['mixed']}/{r['never_pass']}"
              f"               {r['mean_distinct_outputs']}")
    mixed = [o for o in outcomes if 0 < o["passed_of_5"] < N_TRIALS]
    print(f"\nTasks that passed sometimes but not always: {len(mixed)} (see results/task_outcomes.csv)")
    for o in mixed:
        print(f"  {o['model']:13s} {o['language']:11s} {o['condition']:9s} {o['task_id']} "
              f"{o['passed_of_5']}/5 wrong={o['wrong_keys']} failed trials={o['failed_trials']}")
    return summary


if __name__ == "__main__":
    main()
