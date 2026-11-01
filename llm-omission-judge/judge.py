"""Ask a small local model which listed facts are missing from each SOAP note.

This is the omission-detection step of MED-OMIT (Schumacher et al.), run with
qwen2.5:3b and llama3.1:8b instead of GPT-4, on the 80 notes already drafted in
../roman-urdu-soap-benchmark/ (20 cases x English/Roman Urdu x 2 note models).
The facts come from the same case files, so the judge's answer can be compared
fact by fact with the keyword checker used in that benchmark.

One call per note (all facts of the case at once) to keep the run short;
MED-OMIT asks about one fact per call.

Writes results/judgements.csv.

Usage:
    python judge.py                              # both judges, all 80 notes
    python judge.py --judges qwen2.5:3b --limit 4
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent / "roman-urdu-soap-benchmark"
sys.path.insert(0, str(BENCH))
import run as bench  # noqa: E402
from checks import missing_by_fact  # noqa: E402

RES = HERE / "results"
Chat = Callable[[str, str, str], str]

JUDGE_PROMPT = (
    "You check clinical notes for omissions. You get a SOAP note and a numbered list of facts "
    "from the consultation. For each fact, answer \"present\" if the note states it (any wording, "
    "any language), or \"missing\" if the note leaves it out completely or partly. "
    "Reply with JSON only, for example {\"1\": \"present\", \"2\": \"missing\"}."
)
FIELDS = ["judge", "model", "case", "lang", "fact", "critical", "keyword_missing", "judge_missing", "parse_ok"]


def build_user(note: str, facts: List[Dict[str, Any]]) -> str:
    lines = [f"{i}. {f['id'].replace('_', ' ')}: {f['text']}" for i, f in enumerate(facts, 1)]
    return "SOAP note:\n" + note + "\n\nFacts:\n" + "\n".join(lines)


def parse_reply(reply: str, n: int) -> Optional[Dict[int, bool]]:
    """Map fact number -> missing. None if the reply has no usable JSON object."""
    m = re.search(r"\{.*\}", reply, flags=re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    out: Dict[int, bool] = {}
    for k, v in obj.items():
        num = re.sub(r"\D", "", str(k))
        if num and 1 <= int(num) <= n:
            out[int(num)] = "miss" in str(v).lower()
    return out if len(out) == n else None


def load_notes(path: Path = BENCH / "results" / "notes.jsonl") -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def judge_note(chat: Chat, judge: str, note: Dict[str, Any], case: Dict[str, Any]) -> List[Dict[str, Any]]:
    facts = case["facts"]
    user = build_user(note["note"], facts)
    parsed = parse_reply(chat(judge, JUDGE_PROMPT, user), len(facts))
    if parsed is None:  # one retry, then give up on this note
        parsed = parse_reply(chat(judge, JUDGE_PROMPT, user + "\n\nAnswer with the JSON object only."), len(facts))
    kw = missing_by_fact(note["note"], facts)
    rows = []
    for i, f in enumerate(facts, 1):
        rows.append({"judge": judge, "model": note["model"], "case": note["case"], "lang": note["lang"],
                     "fact": f["id"], "critical": bool(f["critical"]), "keyword_missing": bool(kw[f["id"]]),
                     "judge_missing": "" if parsed is None else parsed[i], "parse_ok": parsed is not None})
    return rows


def main(chat: Chat = bench.ollama_chat, argv: Optional[List[str]] = None, out: Path = RES) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judges", nargs="+", default=["qwen2.5:3b", "llama3.1:8b"])
    ap.add_argument("--limit", type=int, default=None, help="only the first N notes (quick test)")
    args = ap.parse_args(argv)
    cases = {c["id"]: c for c in bench.load_cases()}
    notes = load_notes()[: args.limit]
    out.mkdir(exist_ok=True)
    rows: List[Dict[str, Any]] = []
    for judge in args.judges:
        for note in notes:
            t0 = time.time()
            got = judge_note(chat, judge, note, cases[note["case"]])
            rows.extend(got)
            miss = sum(r["judge_missing"] is True for r in got)
            print(f"{judge:12s} judges {note['model']:12s} {note['note_id']:6s} {time.time() - t0:5.1f}s "
                  f"judge_missing={miss:2d} keyword_missing={sum(r['keyword_missing'] for r in got):2d}"
                  f"{'' if got[0]['parse_ok'] else '  PARSE FAILED'}")
    with (out / "judgements.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved {len(rows)} fact judgements to results/judgements.csv. Next: python score.py")


if __name__ == "__main__":
    main()
