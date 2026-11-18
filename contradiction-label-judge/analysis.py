"""Score the binary and three-label judges against code references. No model is called.

Reads results/runs.jsonl and writes:
- results/area_fact.csv   one row per note, judge and prompt: the injured-area fact,
                          its code reference label and the judge's label
- results/summary.csv     per judge, prompt and language: how the judge labelled the
                          injured-area fact for wrong-area, missing-area and correct notes
- results/critical.csv    critical facts the keywords call missing but the judge calls
                          present ("hidden"), binary vs three-label, with McNemar p
- results/to_label.csv    contradicted calls on other facts, for my hand labels
- results/results.json    the main numbers with 95% Wilson intervals
- results/area_fact.png   chart

Reference for the injured-area fact (reads English words in the note only):
- contradicted: the note names the other side, or it never names the injured body
                region but names a region the English transcript does not have
- missing:      not contradicted, and the region or the expected side is absent
- present:      otherwise

Usage:
    python analysis.py
    python analysis.py --score-labels     # after filling my_label in results/to_label.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import contradiction_judge as cj  # noqa: E402  (also puts the benchmark folder on sys.path)
from checks import check_note, missing_by_fact, regions_in  # noqa: E402

RES = HERE / "results"
AREA_IDS = ("injured_area", "side")
COLOURS = {"contradicted": "#1F4E9C", "missing": "#E3A800", "present": "#C8102E"}


def area_reference(note: str, case: Dict[str, Any]) -> str:
    res = check_note(note, case)
    wrong_part = case["main_region"] not in regions_in(note) and bool(res["unsupported_regions"])
    if res["wrong_side"] or wrong_part:
        return "contradicted"
    if not res["main_region_present"] or res["side_present"] is False:
        return "missing"
    return "present"


def wilson(k: int, n: int, z: float = 1.96) -> Tuple[Optional[float], Optional[float]]:
    if n == 0:
        return None, None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return round(max(0.0, c - h), 3), round(min(1.0, c + h), 3)


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p from the two discordant counts."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return float(f"{min(1.0, p):.3g}")


def load_runs(path: Path) -> List[Dict[str, Any]]:
    """Last parsed record per (judge, prompt, key); earlier failed tries are dropped."""
    best: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r.get("parse_ok"):
                best[(r["judge"], r["prompt"], r["key"])] = r
    return list(best.values())


def excerpt(note: str, pattern: str, width: int = 70) -> str:
    m = re.search(pattern, note, flags=re.I) if pattern else None
    if not m:
        return "(no keyword match)"
    a, b = max(0, m.start() - width), min(len(note), m.end() + width)
    return note[a:b].replace("\n", " ")


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def chart(summary: List[Dict[str, Any]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [s for s in summary if s["lang"] == "all" and s["ref"] == "contradicted" and s["notes"]]
    if not rows:
        return
    fig, ax = plt.subplots(figsize=(7.5, 4))
    names = [f"{s['judge']}\n{s['prompt']}" for s in rows]
    bottom = [0.0] * len(rows)
    for lab in ("contradicted", "missing", "present"):
        vals = [100 * s[f"judged_{lab}"] / s["notes"] for s in rows]
        ax.bar(names, vals, bottom=bottom, color=COLOURS[lab], label=f"judged {lab}")
        for i, (v, s) in enumerate(zip(vals, rows)):
            if v >= 6:
                ax.text(i, bottom[i] + v / 2, str(s[f"judged_{lab}"]), ha="center", va="center",
                        color="white", fontsize=8)
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("% of notes with a wrong side or body part")
    ax.set_ylim(0, 100)
    ax.set_title(f"How the judge labelled the injured area in {rows[0]['notes']} notes that got it wrong")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=3)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def score_labels(path: Path) -> None:
    rows = [r for r in csv.DictReader(path.open(encoding="utf-8"))
            if r.get("my_label", "").strip().lower() in cj.LABELS + ("unclear",)]
    if not rows:
        print("No filled labels in", path)
        return
    by: Dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        by[r["judge"]][r["my_label"].strip().lower()] += 1
    for judge, c in sorted(by.items()):
        n = sum(c.values())
        print(f"{judge}: {n} contradicted calls labelled; I agree (contradicted) {c['contradicted']}, "
              f"really missing {c['missing']}, really present {c['present']}, unclear {c['unclear']}")


def main(argv: Optional[List[str]] = None, res: Path = RES, plot: bool = True) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--score-labels", action="store_true")
    args = ap.parse_args(argv)
    if args.score_labels:
        score_labels(res / "to_label.csv")
        return {}

    cases = {c["id"]: c for c in cj.bench.load_cases()}
    notes = {n["key"]: n for n in cj.load_notes()}
    runs = load_runs(res / "runs.jsonl")
    ref_cache: Dict[str, str] = {}
    kw_cache: Dict[str, Dict[str, bool]] = {}

    area_rows: List[Dict[str, Any]] = []
    crit: Dict[Tuple[str, str, str, str], str] = {}  # (judge, key, fact, prompt) -> label, critical kw-missing facts
    label_pool: List[Dict[str, Any]] = []
    for r in runs:
        note, case = notes[r["key"]], cases[r["case"]]
        facts = {f["id"]: f for f in cj.facts_for(case)}
        if r["key"] not in ref_cache:
            ref_cache[r["key"]] = area_reference(note["note"], case)
            kw_cache[r["key"]] = missing_by_fact(note["note"], [f for f in facts.values() if "pattern" in f])
        ref = ref_cache[r["key"]]
        for fid, lab in zip(r["facts"], r["labels"]):
            if fid in AREA_IDS:
                area_rows.append({"judge": r["judge"], "prompt": r["prompt"], "key": r["key"],
                                  "lang": r["lang"], "condition": r["condition"], "case": r["case"],
                                  "reference": ref, "judge_label": lab})
            kw_missing = (ref != "present") if fid in AREA_IDS else kw_cache[r["key"]].get(fid, False)
            if facts[fid]["critical"] and kw_missing:
                crit[(r["judge"], r["key"], fid, r["prompt"])] = lab
            if r["prompt"] == "three" and lab == "contradicted" and fid not in AREA_IDS:
                label_pool.append({"judge": r["judge"], "model": r["model"], "lang": r["lang"],
                                   "condition": r["condition"], "case": r["case"], "fact": fid,
                                   "fact_text": facts[fid]["text"], "critical": facts[fid]["critical"],
                                   "keyword_missing": kw_missing,
                                   "note_text": excerpt(note["note"], str(facts[fid].get("pattern", ""))),
                                   "my_label": "", "my_comment": ""})

    # Injured-area fact: label distribution per reference class.
    summary: List[Dict[str, Any]] = []
    groups: Dict[Tuple[str, str, str, str], Counter] = defaultdict(Counter)
    for a in area_rows:
        for lang in ("all", a["lang"]):
            groups[(a["judge"], a["prompt"], lang, a["reference"])][a["judge_label"]] += 1
    for (judge, prompt, lang, ref), c in sorted(groups.items()):
        n = sum(c.values())
        flagged = c["missing"] + c["contradicted"]
        lo, hi = wilson(flagged, n)
        summary.append({"judge": judge, "prompt": prompt, "lang": lang, "ref": ref, "notes": n,
                        "judged_present": c["present"], "judged_missing": c["missing"],
                        "judged_contradicted": c["contradicted"],
                        "flagged": flagged, "flagged_ci_low": lo, "flagged_ci_high": hi})

    # Paired: wrong-area notes the judge passed as present, binary vs three-label.
    paired: List[Dict[str, Any]] = []
    by_key = {(a["judge"], a["prompt"], a["key"]): a for a in area_rows}
    crit_rows: List[Dict[str, Any]] = []
    for judge in sorted({a["judge"] for a in area_rows}):
        for ref in ("contradicted", "missing", "present"):
            keys = [a["key"] for a in area_rows if a["judge"] == judge and a["prompt"] == "binary"
                    and a["reference"] == ref and (judge, "three", a["key"]) in by_key]
            flag_b = [by_key[(judge, "binary", k)]["judge_label"] != "present" for k in keys]
            flag_t = [by_key[(judge, "three", k)]["judge_label"] != "present" for k in keys]
            b = sum(x and not y for x, y in zip(flag_b, flag_t))
            c = sum(y and not x for x, y in zip(flag_b, flag_t))
            paired.append({"judge": judge, "reference": ref, "paired_notes": len(keys),
                           "flagged_binary": sum(flag_b), "flagged_three": sum(flag_t),
                           "only_binary": b, "only_three": c, "mcnemar_p": mcnemar_exact(b, c)})
        # Critical facts the keywords call missing: how many does the judge call present?
        both = [(k, f) for (j, k, f, p) in crit if j == judge and p == "binary"
                and (judge, k, f, "three") in crit]
        hid_b = [crit[(judge, k, f, "binary")] == "present" for k, f in both]
        hid_t = [crit[(judge, k, f, "three")] == "present" for k, f in both]
        b = sum(x and not y for x, y in zip(hid_b, hid_t))
        c = sum(y and not x for x, y in zip(hid_b, hid_t))
        crit_rows.append({"judge": judge, "critical_facts_missing_by_keywords": len(both),
                          "hidden_binary": sum(hid_b), "hidden_three": sum(hid_t),
                          "only_binary_hid": b, "only_three_hid": c, "mcnemar_p": mcnemar_exact(b, c),
                          "three_called_contradicted": sum(crit[(judge, k, f, "three")] == "contradicted"
                                                           for k, f in both)})

    random.Random(7).shuffle(label_pool)
    to_label = label_pool[:40]

    parse = Counter((r["judge"], r["prompt"]) for r in runs)
    out = {
        "parsed_calls": {f"{j}|{p}": n for (j, p), n in sorted(parse.items())},
        "notes": len(notes),
        "reference_counts": dict(Counter(ref_cache.values())),
        "area_fact": summary, "paired_area_flags": paired, "critical_hidden": crit_rows,
        "contradicted_other_facts": dict(Counter(r["judge"] for r in label_pool)),
    }
    res.mkdir(parents=True, exist_ok=True)
    write_csv(res / "area_fact.csv", area_rows)
    write_csv(res / "summary.csv", summary)
    write_csv(res / "critical.csv", crit_rows)
    write_csv(res / "to_label.csv", to_label)
    (res / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    if plot:
        chart(summary, res / "area_fact.png")

    print("Parsed calls:", out["parsed_calls"])
    print("Reference for the injured-area fact:", out["reference_counts"])
    print("\nInjured-area fact (all languages): judge label by reference")
    print(f"{'judge':12} {'prompt':7} {'reference':13} {'notes':>5} {'present':>8} {'missing':>8} "
          f"{'contradicted':>13} {'flagged 95% CI':>16}")
    for s in summary:
        if s["lang"] == "all":
            print(f"{s['judge']:12} {s['prompt']:7} {s['ref']:13} {s['notes']:>5} {s['judged_present']:>8} "
                  f"{s['judged_missing']:>8} {s['judged_contradicted']:>13} "
                  f"   {s['flagged_ci_low']}-{s['flagged_ci_high']}")
    print("\nPaired flags (missing or contradicted), binary vs three-label:")
    for p in paired:
        print(f"  {p['judge']:12} ref {p['reference']:12} n={p['paired_notes']:3} binary {p['flagged_binary']:3} "
              f"three {p['flagged_three']:3}  McNemar p={p['mcnemar_p']}")
    print("\nCritical facts missing by keywords that the judge called present (hidden):")
    for c in crit_rows:
        print(f"  {c['judge']:12} of {c['critical_facts_missing_by_keywords']:3}: binary {c['hidden_binary']:3}, "
              f"three {c['hidden_three']:3} (McNemar p={c['mcnemar_p']}); "
              f"three-label called {c['three_called_contradicted']} contradicted")
    print(f"\nContradicted calls on other facts: {out['contradicted_other_facts']}; "
          f"{len(to_label)} in results/to_label.csv for hand labels.")
    return out


if __name__ == "__main__":
    main()
