"""Does soft anatomy matching notice a wrong side or a wrong body part?

RaTEScore (Zhao et al. 2024, arXiv:2406.16845) scores a generated report by
pulling out medical entities, embedding them with BioLORD-2023-C, matching each
entity to its most similar entity in the reference, and taking the harmonic mean
of the two directions. The paper does not discuss left and right. In my Roman
Urdu SOAP benchmark the most common errors were a wrong or missing side and a
wrong body part, so this script asks whether that kind of soft matching sees them.

This is a RaTEScore-style score, not RaTEScore itself: no NER model and no learned
type weights. Anatomy phrases are read with the same word lists as
../side-mismatch-check/, then scored with the same encoder (BioLORD-2023-C).

Three parts, no LLM is called:
1. probe:  encoder similarity for fixed pairs (same, synonym, side swap, part swap, unrelated)
2. notes:  the 200 notes from ../side-mismatch-check/, soft score vs the English
           transcript, against a reference label (wrong or missing side, missing main
           region, or a region the transcript never mentions)
3. swaps:  every safe English note with its sides swapped, and with its main body
           part swapped; does the score drop?
The soft score is compared with a code check that needs no encoder.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "side-mismatch-check"))
import side_check as sc  # noqa: E402  (also puts the benchmark folder on sys.path)
from checks import check_note, regions_in  # noqa: E402

RES = HERE / "results"
MODEL = "FremyCompany/BioLORD-2023-C"
Encoder = Callable[[Sequence[str]], np.ndarray]

# Region name -> words used in the phrase given to the encoder.
NAME: Dict[str, str] = {
    "back": "lower back", "neck": "neck", "shoulder": "shoulder", "knee": "knee",
    "hip/groin": "hip", "ankle/foot": "ankle", "wrist/hand": "wrist", "elbow": "elbow",
    "leg": "leg", "arm": "arm", "head": "head", "chest": "chest",
}
# Main body part swaps for the counterfactual notes (English words only).
PART_SWAP: Dict[str, Tuple[str, str]] = {
    "knee": (r"\bknee(s?)\b", r"ankle\1"), "ankle/foot": (r"\bankle(s?)\b", r"knee\1"),
    "shoulder": (r"\bshoulder(s?)\b", r"elbow\1"), "elbow": (r"\belbow(s?)\b", r"shoulder\1"),
    "back": (r"\b(lower |low )?back\b", r"neck"), "neck": (r"\bneck\b", r"lower back"),
    "hip/groin": (r"\bhip(s?)\b", r"knee\1"), "wrist/hand": (r"\bwrist(s?)\b", r"elbow\1"),
}
PROBE: List[Tuple[str, str, str]] = [
    ("same", "right knee", "right knee"),
    ("synonym", "lower back", "lumbar spine"),
    ("synonym", "right knee", "right patella"),
    ("side swap", "right knee", "left knee"),
    ("side swap", "left shoulder", "right shoulder"),
    ("side swap", "right ankle", "left ankle"),
    ("part swap", "right ankle", "right knee"),
    ("part swap", "left shoulder", "left elbow"),
    ("part swap", "lower back", "neck"),
    ("unrelated", "knee", "headache"),
]


def regions_any(text: str) -> Set[str]:
    """Body regions in English words or Roman Urdu words."""
    found = set(regions_in(text))
    for tok in re.findall(r"[A-Za-z]+", text):
        for pat, reg in sc.PART_RES:
            if pat.match(tok):
                found.add(reg)
    return found


def anatomy(text: str) -> Set[str]:
    """Anatomy phrases: 'right knee' when a side is attached, else 'knee'."""
    pairs = sc.side_parts(text)
    sided = {r for _, r in pairs}
    out = {f"{s} {NAME[r]}" for s, r in pairs if r in NAME}
    out |= {NAME[r] for r in regions_any(text) - sided if r in NAME}
    return out


def soft_score(ref: Set[str], cand: Set[str], enc: Encoder,
               cache: Optional[Dict[str, np.ndarray]] = None) -> float:
    """Harmonic mean of best-match cosine in both directions (RaTEScore Eqs. 1-3, no weights)."""
    if not ref and not cand:
        return 1.0
    if not ref or not cand:
        return 0.0
    cache = {} if cache is None else cache
    new = [p for p in sorted(ref | cand) if p not in cache]
    if new:
        for p, v in zip(new, enc(new)):
            cache[p] = v / (np.linalg.norm(v) or 1.0)
    R = np.stack([cache[p] for p in sorted(ref)])
    C = np.stack([cache[p] for p in sorted(cand)])
    sim = C @ R.T
    p_, r_ = float(sim.max(axis=1).mean()), float(sim.max(axis=0).mean())
    return 0.0 if p_ + r_ <= 0 else 2 * p_ * r_ / (p_ + r_)


def code_check(transcript: str, note: str) -> bool:
    """Flag when sides disagree (side_set) or body regions disagree, reading only
    the spoken transcript and the note."""
    if sc.run_checks(transcript, note)["side_set"]:
        return True
    t, n = regions_any(transcript), regions_any(note)
    return bool(n - t) or (bool(t) and not (t & n))


def label(note: str, case: Dict[str, Any]) -> Dict[str, bool]:
    """Reference label from the English transcript and the case's known side and region."""
    side = sc.reference(note, case)
    res = check_note(note, case)
    part = (not res["main_region_present"]) or bool(res["unsupported_regions"])
    return {"side_unsafe": bool(side["ref_unsafe"]), "part_unsafe": part,
            "unsafe": bool(side["ref_unsafe"]) or part}


def swap_sides(text: str) -> str:
    return re.sub(r"\b(left|right|Left|Right)\b",
                  lambda m: {"left": "right", "right": "left", "Left": "Right",
                             "Right": "Left"}[m.group(1)], text)


def swap_part(text: str, region: str) -> Optional[str]:
    if region not in PART_SWAP:
        return None
    pat, rep = PART_SWAP[region]
    out = re.sub(pat, rep, text, flags=re.IGNORECASE)
    return out if out != text else None


def auroc(unsafe: Sequence[float], safe: Sequence[float]) -> float:
    """Chance that an unsafe note scores lower than a safe note (ties count half)."""
    if not unsafe or not safe:
        return float("nan")
    wins = sum((u < s) + 0.5 * (u == s) for u in unsafe for s in safe)
    return round(wins / (len(unsafe) * len(safe)), 3)


def threshold(safe_scores: Sequence[float], q: float = 5.0) -> float:
    """Flag below this: the score that flags about q% of safe notes."""
    return float(np.percentile(np.asarray(safe_scores), q)) if safe_scores else 0.0


def bioLORD(model: str = MODEL) -> Encoder:
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(model, device="cpu")
    return lambda xs: m.encode(list(xs), normalize_embeddings=True, convert_to_numpy=True)


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def chart(summary: List[Dict[str, Any]], path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 4))
    width = 0.38
    for j, (name, col, colour) in enumerate([("Soft anatomy score", "soft_caught", "#1F4E9C"),
                                              ("Code check", "code_caught", "#E3A800")]):
        xs = [i + (j - 0.5) * width for i in range(len(summary))]
        vals = [100 * r[col] / r["n"] if r["n"] else 0 for r in summary]
        ax.bar(xs, vals, width, label=name, color=colour)
        for x, v, r in zip(xs, vals, summary):
            ax.text(x, v + 1, f"{r[col]}/{r['n']}", ha="center", fontsize=8)
    ax.set_xticks(range(len(summary)))
    ax.set_xticklabels([r["set"] for r in summary], fontsize=8)
    ax.set_ylabel("% flagged")
    ax.set_ylim(0, 110)
    ax.set_title("Flagged at the cut that flags ~5% of safe notes")
    ax.legend(frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main(argv: Optional[List[str]] = None, enc: Optional[Encoder] = None,
         out: Path = RES) -> Dict[str, Any]:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args(argv)
    enc = enc or bioLORD(args.model)
    cache: Dict[str, np.ndarray] = {}

    probe = []
    for kind, a, b in PROBE:
        probe.append({"kind": kind, "a": a, "b": b,
                      "cosine": round(soft_score({a}, {b}, enc, cache), 3)})

    cases = sc.load_cases()
    rows: List[Dict[str, Any]] = []
    for r in sc.load_notes():
        case = cases[r["case"]]
        spoken = case["en"] if r["lang"] == "en" else case["ru"]
        ref, cand = anatomy(case["en"]), anatomy(r["note"])
        rows.append({**{k: r[k] for k in ("model", "lang", "condition", "case")},
                     **label(r["note"], case),
                     "soft": round(soft_score(ref, cand, enc, cache), 4),
                     "code_flag": code_check(spoken, r["note"]),
                     "ref_anatomy": "; ".join(sorted(ref)),
                     "note_anatomy": "; ".join(sorted(cand))})

    safe_scores = [x["soft"] for x in rows if not x["unsafe"]]
    t = threshold(safe_scores)

    swaps: List[Dict[str, Any]] = []
    for r, x in zip(sc.load_notes(), rows):
        if r["lang"] != "en" or x["unsafe"]:
            continue
        case = cases[r["case"]]
        ref = anatomy(case["en"])
        variants = [("side swap", swap_sides(r["note"]) if case.get("side") else None),
                    ("part swap", swap_part(r["note"], case["main_region"]))]
        for kind, text in variants:
            if not text or text == r["note"]:
                continue
            s = soft_score(ref, anatomy(text), enc, cache)
            swaps.append({"kind": kind, "model": r["model"], "case": r["case"],
                          "soft_before": x["soft"], "soft_after": round(s, 4),
                          "drop": round(x["soft"] - s, 4),
                          "soft_flag": s < t, "code_flag": code_check(case["en"], text),
                          "unsafe_by_label": label(text, case)["unsafe"]})

    def block(name: str, scores: List[float], code: List[bool]) -> Dict[str, Any]:
        return {"set": name, "n": len(scores), "soft_caught": sum(s < t for s in scores),
                "code_caught": sum(code)}

    uns = [x for x in rows if x["unsafe"]]
    saf = [x for x in rows if not x["unsafe"]]
    summary = [
        block("Real unsafe notes", [x["soft"] for x in uns], [x["code_flag"] for x in uns]),
        block("Real side errors", [x["soft"] for x in uns if x["side_unsafe"]],
              [x["code_flag"] for x in uns if x["side_unsafe"]]),
        block("Real body-part errors", [x["soft"] for x in uns if x["part_unsafe"]],
              [x["code_flag"] for x in uns if x["part_unsafe"]]),
        block("Side swaps", [w["soft_after"] for w in swaps if w["kind"] == "side swap"],
              [w["code_flag"] for w in swaps if w["kind"] == "side swap"]),
        block("Part swaps", [w["soft_after"] for w in swaps if w["kind"] == "part swap"],
              [w["code_flag"] for w in swaps if w["kind"] == "part swap"]),
        block("Safe notes (false flags)", [x["soft"] for x in saf], [x["code_flag"] for x in saf]),
    ]
    for s in summary:
        s["cut"] = round(t, 4)
    stats = {"notes": len(rows), "unsafe": len(uns), "safe": len(saf), "cut": round(t, 4),
             "auroc_soft": auroc([x["soft"] for x in uns], safe_scores),
             "mean_soft_unsafe": round(float(np.mean([x["soft"] for x in uns])), 3) if uns else "",
             "mean_soft_safe": round(float(np.mean(safe_scores)), 3) if saf else "",
             "mean_drop_side_swap": round(float(np.mean([w["drop"] for w in swaps if w["kind"] == "side swap"] or [0])), 3),
             "mean_drop_part_swap": round(float(np.mean([w["drop"] for w in swaps if w["kind"] == "part swap"] or [0])), 3)}

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "probe.csv", probe)
    write_csv(out / "per_note.csv", rows)
    if swaps:
        write_csv(out / "swaps.csv", swaps)
    write_csv(out / "summary.csv", summary)
    write_csv(out / "stats.csv", [stats])
    chart(summary, out / "soft_vs_code.png")

    print("Encoder similarity (1 = identical):")
    for p in probe:
        print(f"  {p['kind']:10} {p['a']:>14} | {p['b']:<14} {p['cosine']}")
    print(f"\n{stats}\n")
    print(f"{'set':26} {'n':>4} {'soft caught':>12} {'code caught':>12}")
    for s in summary:
        print(f"{s['set']:26} {s['n']:>4} {s['soft_caught']:>12} {s['code_caught']:>12}")
    print(f"\nWrote {out}/probe.csv, per_note.csv, swaps.csv, summary.csv, stats.csv, soft_vs_code.png")
    return stats


if __name__ == "__main__":
    main()
