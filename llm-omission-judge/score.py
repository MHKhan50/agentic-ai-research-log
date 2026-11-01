"""Compare the LLM omission judge with the keyword checker.

Reads results/judgements.csv and writes:
- results/agreement.csv      per judge and note language: agreement, Cohen's kappa,
                             facts each method calls missing, and both disagreement kinds
- results/weighted.csv       MED-OMIT-style weighted omission score per note
                             (critical fact = 1, other fact = 0.1), mean per note model and language
- results/disagreements.csv  every fact where judge and keywords differ, with blank
                             columns for my own label
- results/agreement.png      kappa per judge and language
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
WEIGHTS = {True: 1.0, False: 0.1}  # MED-OMIT: critical 1, important 0.5, other 0.1 (no middle tier here)


def as_bool(x: object) -> bool:
    return str(x).strip().lower() == "true"


def cohen_kappa(a: Sequence[bool], b: Sequence[bool]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def load(path: Path = RES / "judgements.csv") -> List[Dict[str, str]]:
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def agreement(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    groups: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for r in rows:
        groups[(r["judge"], r["lang"])].append(r)
    out = []
    for (judge, lang), rs in sorted(groups.items()):
        ok = [r for r in rs if as_bool(r["parse_ok"])]
        kw = [as_bool(r["keyword_missing"]) for r in ok]
        jd = [as_bool(r["judge_missing"]) for r in ok]
        out.append({
            "judge": judge, "lang": lang, "facts": len(rs), "parsed": len(ok),
            "agree_pct": round(100 * sum(x == y for x, y in zip(kw, jd)) / len(ok), 1) if ok else "",
            "kappa": round(cohen_kappa(kw, jd), 3) if ok else "",
            "keyword_missing": sum(kw), "judge_missing": sum(jd),
            "judge_only": sum(j and not k for k, j in zip(kw, jd)),
            "keyword_only": sum(k and not j for k, j in zip(kw, jd)),
            "critical_judge_only": sum(j and not k and as_bool(r["critical"]) for r, k, j in zip(ok, kw, jd)),
        })
    return out


def weighted(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    """Mean weighted omission score per note; keyword score taken once per note, judge score per judge."""
    notes: Dict[Tuple[str, str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for r in rows:
        notes[(r["judge"], r["model"], r["lang"], r["case"])].append(r)
    acc: Dict[Tuple[str, str, str], List[float]] = defaultdict(list)
    seen_kw = set()
    for (judge, model, lang, case), rs in notes.items():
        w = [WEIGHTS[as_bool(r["critical"])] for r in rs]
        if (model, lang, case) not in seen_kw:
            seen_kw.add((model, lang, case))
            acc[("keywords", model, lang)].append(sum(x for x, r in zip(w, rs) if as_bool(r["keyword_missing"])))
        if all(as_bool(r["parse_ok"]) for r in rs):
            acc[(judge, model, lang)].append(sum(x for x, r in zip(w, rs) if as_bool(r["judge_missing"])))
    return [{"scorer": s, "model": m, "lang": l, "notes": len(v), "mean_weighted_omissions": round(sum(v) / len(v), 2)}
            for (s, m, l), v in sorted(acc.items())]


def disagreements(rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    return [{**{k: r[k] for k in ("judge", "model", "case", "lang", "fact", "critical",
                                  "keyword_missing", "judge_missing")}, "my_label": "", "my_comment": ""}
            for r in rows if as_bool(r["parse_ok"]) and as_bool(r["keyword_missing"]) != as_bool(r["judge_missing"])]


def write_csv(path: Path, rows: List[Dict[str, object]], fields: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(fields))
        w.writeheader()
        w.writerows(rows)


def chart(agr: List[Dict[str, object]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    judges = sorted({str(a["judge"]) for a in agr})
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for i, lang in enumerate(("en", "ru")):
        vals = [next((float(a["kappa"]) for a in agr if a["judge"] == j and a["lang"] == lang and a["kappa"] != ""), 0.0)
                for j in judges]
        ax.bar([x + i * 0.38 for x in range(len(judges))], vals, 0.38,
               label="English notes" if lang == "en" else "Roman Urdu notes", color=("#1f4e79", "#e07b39")[i])
    ax.set_xticks([x + 0.19 for x in range(len(judges))])
    ax.set_xticklabels(judges)
    ax.set_ylabel("Cohen's kappa vs keyword checker")
    ax.set_ylim(-0.1, 1)
    ax.axhline(0, color="grey", lw=0.6)
    ax.legend(frameon=False)
    ax.set_title("Omission judge agreement with keyword checks")
    fig.tight_layout()
    fig.savefig(path, dpi=150)


def main(res: Path = RES, plot: bool = True) -> None:
    rows = load(res / "judgements.csv")
    agr, wtd, dis = agreement(rows), weighted(rows), disagreements(rows)
    write_csv(res / "agreement.csv", agr, list(agr[0]))
    write_csv(res / "weighted.csv", wtd, list(wtd[0]))
    write_csv(res / "disagreements.csv", dis,
              ["judge", "model", "case", "lang", "fact", "critical", "keyword_missing", "judge_missing",
               "my_label", "my_comment"])
    if plot:
        chart(agr, res / "agreement.png")
    for a in agr:
        print(a)
    print()
    for w in wtd:
        print(w)
    print(f"\n{len(dis)} disagreements in results/disagreements.csv")


if __name__ == "__main__":
    main()
