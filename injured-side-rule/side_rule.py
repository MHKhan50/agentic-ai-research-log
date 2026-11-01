"""Can a side rule stop the injured side disappearing from Roman Urdu SOAP notes?

Uses the 20 consultations, the note prompt and the checks of
../roman-urdu-soap-benchmark/. Only the Roman Urdu transcripts are drafted.

Conditions:
- baseline: the Roman Urdu notes already drafted in roman-urdu-soap-benchmark
  (same prompt, temperature 0, seed 42), read from its results/notes.jsonl.
- rule: the prompt also asks the model to state the side.
- rule_glossary: the rule plus a two-line glossary of Roman Urdu side words.
- retry: the baseline note is checked; if the transcript has a side word and
  the note names no side, the model is asked once to rewrite it. A note still
  without a side is marked incomplete for the physiotherapist.

The retry trigger only looks at the Roman Urdu transcript, as a real pipeline
would; it does not know the expected answer.

Writes results/notes.jsonl and results/per_note.csv.

Usage:
    python side_rule.py              # resumes if stopped; --fresh starts again
    python side_rule.py --models llama3.1:8b --cases C2 C3 --conditions rule
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
from checks import check_note, sides_in  # noqa: E402

RES = HERE / "results"
BASELINE_NOTES = BENCH / "results" / "notes.jsonl"
CONDITIONS = ("baseline", "rule", "rule_glossary", "retry")
MODELS = ("qwen2.5:3b", "llama3.1:8b")

SIDE_RULE = (
    " If the patient or physiotherapist says which side of the body is affected, "
    "write that side (left or right) next to the body part every time it is named."
)
GLOSSARY = (
    " Roman Urdu side words: daayan, daayen, dayan mean right; "
    "baayan, baayen, bayan mean left."
)
PROMPTS = {
    "rule": bench.NOTE_PROMPT + SIDE_RULE,
    "rule_glossary": bench.NOTE_PROMPT + SIDE_RULE + GLOSSARY,
}
RETRY_FEEDBACK = (
    "The draft note below does not say which side of the body is affected, but the "
    "transcript does. Rewrite the complete SOAP note with the same four headings, and "
    "write the side (left or right) next to the body part. Do not add anything that is "
    "not in the transcript."
)
RU_SIDE = re.compile(r"\b(daa?y[ae]n|baa?y[ae]n|left|right)\b", re.IGNORECASE)

Chat = Callable[[str, str, str], str]
MAX_TOKENS = 1024  # a SOAP note is 200-500 tokens; this stops a model that repeats itself forever
CUT_MARK = "[cut at 1024 tokens]"


def ollama_chat(model: str, system: str, user: str, timeout: int = 300) -> str:
    """Same request as the benchmark (temperature 0, seed 42) plus a length cap.

    qwen2.5:3b stalled on one note with no cap: it kept generating until the
    5-minute timeout, three times in a row. A capped note is kept and marked.
    """
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42, "num_predict": MAX_TOKENS},
    }
    resp = bench.requests.post(bench.OLLAMA_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    body = resp.json()
    note = body["message"]["content"]
    if body.get("done_reason") == "length":
        note += "\n" + CUT_MARK
    return note


def transcript_has_side(ru: str) -> bool:
    """What the pipeline can see: a side word anywhere in the Roman Urdu transcript."""
    return bool(RU_SIDE.search(ru))


def side_checks(note: str, case: Dict[str, Any]) -> Dict[str, Any]:
    """Benchmark checks plus a side named that the English transcript does not support."""
    res = check_note(note, case)
    res["any_side_named"] = bool(sides_in(note))
    res["unsupported_side"] = bool(sides_in(note) - sides_in(str(case["en"])))
    return res


def load_baseline(path: Path = BASELINE_NOTES) -> Dict[tuple, Dict[str, Any]]:
    out: Dict[tuple, Dict[str, Any]] = {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["lang"] == "ru":
                out[(r["model"], r["case"])] = r
    return out


def retry_message(case: Dict[str, Any], note: str) -> str:
    return f"Transcript:\n{case['ru']}\n\n{RETRY_FEEDBACK}\n\nDraft note:\n{note}"


def draft(condition: str, model: str, case: Dict[str, Any], chat: Chat,
          baseline: Dict[tuple, Dict[str, Any]]) -> Dict[str, Any]:
    t0 = time.time()
    retried = False
    if condition in PROMPTS:
        note = chat(model, PROMPTS[condition], "Transcript:\n" + case["ru"])
        secs = time.time() - t0
    else:
        base = baseline[(model, case["id"])]
        note, secs = base["note"], float(base["seconds"])
        if condition == "retry" and transcript_has_side(case["ru"]) and not sides_in(note):
            retried = True
            t1 = time.time()
            note = chat(model, bench.NOTE_PROMPT, retry_message(case, note))
            secs += time.time() - t1
    return {"note": note, "seconds": round(secs, 1), "retried": retried}


def chat_with_retry(chat: Chat, model: str, system: str, user: str, tries: int = 2) -> str:
    """Ollama sometimes stalls on a long run; wait and try the same request again."""
    for attempt in range(tries):
        try:
            return chat(model, system, user)
        except Exception as exc:  # requests.Timeout, ConnectionError
            if attempt == tries - 1:
                raise
            print(f"  {type(exc).__name__}, waiting 20 s and trying again")
            time.sleep(20)
    raise RuntimeError("unreachable")


def main(chat: Chat = ollama_chat, argv: Optional[List[str]] = None, out: Path = RES,
         baseline_path: Path = BASELINE_NOTES) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--cases", nargs="+", default=None)
    ap.add_argument("--conditions", nargs="+", default=list(CONDITIONS), choices=CONDITIONS)
    ap.add_argument("--fresh", action="store_true", help="ignore notes already saved and start again")
    args = ap.parse_args(argv)
    cases = [c for c in bench.load_cases() if not args.cases or c["id"] in args.cases]
    by_id = {c["id"]: c for c in cases}
    baseline = load_baseline(baseline_path)
    out.mkdir(exist_ok=True)
    notes_path = out / "notes.jsonl"
    done: Dict[tuple, Dict[str, Any]] = {}
    if notes_path.exists() and not args.fresh:
        for line in notes_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                done[(r["model"], r["condition"], r["case"])] = r
        print(f"Resuming: {len(done)} notes already saved")

    def safe_chat(model: str, system: str, user: str) -> str:
        return chat_with_retry(chat, model, system, user)

    with notes_path.open("w" if args.fresh else "a", encoding="utf-8") as fh:
        for model in args.models:
            for cond in args.conditions:
                for case in cases:
                    key = (model, cond, case["id"])
                    if key in done:
                        continue
                    d = draft(cond, model, case, safe_chat, baseline)
                    rec = {"model": model, "condition": cond, "case": case["id"], **d}
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                    done[key] = rec
                    res = side_checks(d["note"], case)
                    print(f"{model:12s} {cond:13s} {case['id']:4s} {d['seconds']:5.1f}s"
                          f"  side={res['side_present']!s:5s} unsupported_side={res['unsupported_side']!s:5s}"
                          f"  missing={res['facts_missing']:2d} critical={res['critical_missing']}"
                          f"{'  RETRIED' if d['retried'] else ''}{'  CUT' if CUT_MARK in d['note'] else ''}")
    rows: List[Dict[str, Any]] = []
    for (model, cond, cid), rec in done.items():
        if model not in args.models or cond not in args.conditions or cid not in by_id:
            continue
        case = by_id[cid]
        res = side_checks(rec["note"], case)
        incomplete = transcript_has_side(case["ru"]) and not res["any_side_named"]
        rows.append({"model": model, "condition": cond, "case": cid, "seconds": rec["seconds"],
                     "retried": rec["retried"], "cut_at_cap": CUT_MARK in rec["note"],
                     "marked_incomplete": incomplete, **res})
    with (out / "per_note.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved {len(rows)} notes to results/. Next: python side_summary.py")


if __name__ == "__main__":
    main()
