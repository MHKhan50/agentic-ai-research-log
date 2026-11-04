"""Code side check for SOAP notes: compare the side words in the transcript with the note.

Earlier runs (../injured-side-rule/) showed that asking a small model to write
the injured side made it write the wrong side more often. This script tests the
proposal from that write-up: do not leave the side to the model; read the side
words in the transcript with code, compare them with the note, and send any
mismatch to the physiotherapist.

No model is called. The input is the 200 notes already drafted:
- 40 English notes from ../roman-urdu-soap-benchmark/ (2 models x 20 cases)
- 160 Roman Urdu notes from ../injured-side-rule/ (2 models x 4 conditions x 20)

Three checks, each reading only what a real pipeline sees (the transcript in
the language spoken, and the note):
- present:   flag if the transcript has a side word and the note has none
             (the check used by the retry condition before)
- side_set:  also flag if the note names a side the transcript never says
- side_part: also flag if the note puts a side on a body part (same limb group)
             where the transcript puts the other side

The reference label comes from the English transcript and the case's injured
side, using the benchmark checks: a note is unsafe on side if the injured side
is missing, the other side is named, or a side is named that the English
transcript does not contain.
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BENCH = ROOT / "roman-urdu-soap-benchmark"
sys.path.insert(0, str(BENCH))
import run as bench  # noqa: E402  (load_cases adds side and region to the pilot cases)
from checks import REGIONS, check_note, sides_in  # noqa: E402

RES = HERE / "results"
BENCH_NOTES = BENCH / "results" / "notes.jsonl"
RULE_NOTES = ROOT / "injured-side-rule" / "results" / "notes.jsonl"

CHECKS = ("present", "side_set", "side_part")

# Side words. Roman Urdu spellings seen in the transcripts plus common variants.
SIDE_WORDS: Dict[str, str] = {
    "right": "right", "daayan": "right", "daayen": "right", "dayan": "right",
    "dayen": "right", "daaen": "right", "daain": "right",
    "left": "left", "baayan": "left", "baayen": "left", "bayan": "left",
    "bayen": "left", "baaen": "left", "baain": "left",
}
SIDE_RE = re.compile(r"\b(" + "|".join(sorted(SIDE_WORDS, key=len, reverse=True)) + r")\b",
                     re.IGNORECASE)

# Roman Urdu body words -> benchmark region names.
RU_PARTS: Dict[str, str] = {
    r"ghutn[aei]": "knee", r"kandh[aei]": "shoulder", r"takhn[aei]": "ankle/foot",
    r"a+edi": "ankle/foot", r"pai?r": "ankle/foot", r"achilles": "ankle/foot",
    r"koolh[aei]": "hip/groin", r"kohni": "elbow", r"haath\w*": "wrist/hand",
    r"angooth[aei]": "wrist/hand", r"ungli\w*": "wrist/hand", r"kalai": "wrist/hand",
    r"baazu\w*": "arm", r"taang\w*": "leg", r"pindli": "leg", r"ra+n": "leg",
    r"gardan": "neck", r"kamar": "back", r"sar": "head",
}
PART_RES: List[Tuple[re.Pattern, str]] = (
    [(re.compile(r"^" + p + r"$", re.IGNORECASE), r) for p, r in RU_PARTS.items()]
)
EN_REGION_RES: List[Tuple[re.Pattern, str]] = [(re.compile(p), r) for r, p in REGIONS.items()]

GROUPS: Dict[str, str] = {
    "shoulder": "upper", "elbow": "upper", "wrist/hand": "upper", "arm": "upper",
    "hip/groin": "lower", "knee": "lower", "leg": "lower", "ankle/foot": "lower",
    "neck": "axial", "back": "axial", "head": "axial", "chest": "axial",
}
WINDOW = 4  # words after a side word in which a body part is attached to it
OTHER = {"left": "right", "right": "left"}


def side_words(text: str) -> Set[str]:
    """Sides named anywhere, English or Roman Urdu spelling."""
    return {SIDE_WORDS[m.lower()] for m in SIDE_RE.findall(text)}


def _region_of(words: List[str]) -> Optional[str]:
    """First body region in a short run of words, Roman Urdu word list first, then English."""
    for w in words:
        for pat, reg in PART_RES:
            if pat.match(w):
                return reg
    joined = " ".join(words).lower()
    best: Optional[Tuple[int, str]] = None
    for pat, reg in EN_REGION_RES:
        m = pat.search(joined)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), reg)
    return best[1] if best else None


def side_parts(text: str, window: int = WINDOW) -> Set[Tuple[str, str]]:
    """(side, region) pairs: a side word followed by a body part within `window` words."""
    tokens = re.findall(r"[A-Za-z]+", text)
    out: Set[Tuple[str, str]] = set()
    for i, tok in enumerate(tokens):
        side = SIDE_WORDS.get(tok.lower())
        if side:
            reg = _region_of(tokens[i + 1:i + 1 + window])
            if reg:
                out.add((side, reg))
    return out


def run_checks(transcript: str, note: str) -> Dict[str, bool]:
    """The three checks. Each one reads only the spoken transcript and the note."""
    t_sides, n_sides = side_words(transcript), side_words(note)
    present = bool(t_sides) and not n_sides
    side_set = present or bool(n_sides - t_sides)
    t_pairs, n_pairs = side_parts(transcript), side_parts(note)
    clash = False
    for side, reg in n_pairs:
        group = GROUPS.get(reg)
        same = {(s, r) for s, r in t_pairs if GROUPS.get(r) == group}
        if same and (OTHER[side], reg) in same or (
                same and not any(s == side for s, _ in same)):
            clash = True
            break
    return {"present": present, "side_set": side_set, "side_part": side_set or clash}


def reference(note: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """Reference label from the English transcript and the known injured side."""
    res = check_note(note, case)
    missing = res["side_present"] is False
    wrong = bool(res["wrong_side"])
    unsupported = bool(sides_in(note) - sides_in(str(case["en"])))
    return {"ref_missing": missing, "ref_wrong": wrong, "ref_unsupported": unsupported,
            "ref_unsafe": missing or wrong or unsupported}


def load_cases() -> Dict[str, Dict[str, Any]]:
    return {c["id"]: c for c in bench.load_cases()}


def load_notes(bench: Path = BENCH_NOTES, rule: Path = RULE_NOTES) -> List[Dict[str, Any]]:
    """English notes from the benchmark and every Roman Urdu note from the side-rule run."""
    rows: List[Dict[str, Any]] = []
    with bench.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["lang"] == "en":
                rows.append({"model": r["model"], "lang": "en", "condition": "baseline",
                             "case": r["case"], "note": r["note"]})
    with rule.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            rows.append({"model": r["model"], "lang": "ru", "condition": r["condition"],
                         "case": r["case"], "note": r["note"]})
    return rows


def score(rows: Iterable[Dict[str, Any]], check: str) -> Dict[str, Any]:
    """Catch rate on unsafe notes and false flags on safe notes for one check."""
    rows = list(rows)
    unsafe = [r for r in rows if r["ref_unsafe"]]
    safe = [r for r in rows if not r["ref_unsafe"]]
    wrong = [r for r in rows if r["ref_wrong"] or r["ref_unsupported"]]
    miss = [r for r in rows if r["ref_missing"]]
    def n(xs: List[Dict[str, Any]]) -> int:
        return sum(bool(r[check]) for r in xs)
    return {
        "check": check, "notes": len(rows), "flagged": n(rows),
        "unsafe": len(unsafe), "unsafe_caught": n(unsafe),
        "wrong_or_unsupported": len(wrong), "wrong_caught": n(wrong),
        "missing": len(miss), "missing_caught": n(miss),
        "safe": len(safe), "safe_flagged": n(safe),
        "catch_rate": round(n(unsafe) / len(unsafe), 3) if unsafe else "",
        "false_flag_rate": round(n(safe) / len(safe), 3) if safe else "",
    }


def label_sample(rows: List[Dict[str, Any]], k: int = 20, seed: int = 7) -> List[Dict[str, Any]]:
    """Notes for hand labelling: every disagreement between side_part and the reference,
    then a fixed random sample of the rest, up to k notes in all."""
    dis = [r for r in rows if bool(r["side_part"]) != bool(r["ref_unsafe"])]
    rest = [r for r in rows if r not in dis]
    random.Random(seed).shuffle(rest)
    return (dis + rest)[:max(k, len(dis))]


def side_snippets(text: str, width: int = 50) -> str:
    """Short text around each side word, so a note can be labelled without opening it."""
    bits = []
    for m in SIDE_RE.finditer(text):
        a, b = max(0, m.start() - width), min(len(text), m.end() + width)
        bits.append(text[a:b].replace("\n", " "))
    return " | ".join(bits) if bits else "(no side word)"


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
    rows = [r for r in summary if r["group"] == "all"]
    labels = [r["check"] for r in rows]
    bars = [("Unsafe notes caught", "unsafe_caught", "unsafe", "#1f6f8b"),
            ("Safe notes flagged", "safe_flagged", "safe", "#d9822b")]
    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.38
    for j, (name, num, den, colour) in enumerate(bars):
        vals = [100 * r[num] / r[den] if r[den] else 0 for r in rows]
        xs = [i + (j - 0.5) * width for i in range(len(rows))]
        ax.bar(xs, vals, width, label=name, color=colour)
        for x, v, r in zip(xs, vals, rows):
            ax.text(x, v + 1, f"{r[num]}/{r[den]}", ha="center", fontsize=8)
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels(labels)
    ax.set_ylabel("% of notes")
    ax.set_ylim(0, 110)
    ax.set_title("Code side check on 200 SOAP notes (English and Roman Urdu)")
    ax.legend(frameon=False)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def score_labels(path: Path) -> Optional[Dict[str, Any]]:
    """Agreement of each check with my hand labels (my_label: safe or unsafe)."""
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("my_label", "").strip().lower() in ("safe", "unsafe")]
    if not rows:
        return None
    out: Dict[str, Any] = {"labelled": len(rows)}
    for col in ("ref_unsafe",) + CHECKS:
        agree = sum((r[col] == "True") == (r["my_label"].strip().lower() == "unsafe") for r in rows)
        out[col] = f"{agree}/{len(rows)}"
    return out


def main(argv: Optional[List[str]] = None, out: Path = RES) -> List[Dict[str, Any]]:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--labels", type=Path, default=out / "to_label.csv",
                    help="score my filled-in labels instead of writing a new sheet")
    ap.add_argument("--score-labels", action="store_true")
    args = ap.parse_args(argv)
    if args.score_labels:
        res = score_labels(args.labels)
        print(res if res else "No filled labels found in " + str(args.labels))
        return []

    cases = load_cases()
    rows: List[Dict[str, Any]] = []
    for r in load_notes():
        case = cases[r["case"]]
        transcript = case["en"] if r["lang"] == "en" else case["ru"]
        rows.append({**{k: r[k] for k in ("model", "lang", "condition", "case")},
                     "injured_side": case.get("side") or "",
                     **reference(r["note"], case), **run_checks(transcript, r["note"]),
                     "note_sides": "; ".join(sorted(side_words(r["note"]))),
                     "transcript_sides": "; ".join(sorted(side_words(transcript))),
                     "_note": r["note"]})

    groups = [("all", rows), ("en", [r for r in rows if r["lang"] == "en"]),
              ("ru", [r for r in rows if r["lang"] == "ru"])]
    summary = [{"group": g, **score(rs, c)} for g, rs in groups for c in CHECKS]

    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "per_note.csv", [{k: v for k, v in r.items() if k != "_note"} for r in rows])
    write_csv(out / "summary.csv", summary)
    sheet = [{**{k: r[k] for k in ("model", "lang", "condition", "case", "injured_side",
                                     "ref_unsafe") + CHECKS},
              "side_text": side_snippets(r["_note"]), "my_label": "", "my_comment": ""}
             for r in label_sample(rows)]
    write_csv(out / "to_label.csv", sheet)
    chart(summary, out / "catch_vs_false_flags.png")

    print(f"{'group':5} {'check':10} {'flagged':>8} {'unsafe caught':>14} {'wrong caught':>13} "
          f"{'missing caught':>15} {'safe flagged':>13}")
    for s in summary:
        print(f"{s['group']:5} {s['check']:10} {s['flagged']:>8} "
              f"{s['unsafe_caught']:>6}/{s['unsafe']:<7} {s['wrong_caught']:>5}/{s['wrong_or_unsupported']:<7} "
              f"{s['missing_caught']:>6}/{s['missing']:<8} {s['safe_flagged']:>5}/{s['safe']:<7}")
    print(f"\nWrote {out}/per_note.csv, summary.csv, to_label.csv ({len(sheet)} notes) "
          "and catch_vs_false_flags.png")
    return rows


if __name__ == "__main__":
    main()
