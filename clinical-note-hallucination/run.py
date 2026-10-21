"""Draft a SOAP note for each consultation (English and Roman Urdu) with a local model,
then run the automatic checks.

Writes:
  results/notes.jsonl     every drafted note
  results/omissions.csv   one row per listed fact: kept or missing
  results/review.csv      sentences for a clinician to label (flagged or in the Plan)

Usage:
    python run.py                     # qwen2.5:3b
    python run.py --model llama3.1:8b
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

from note_checks import missing_facts, review_reason, sentence_flags, split_sections

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
OLLAMA_URL = "http://localhost:11434/api/chat"
LANG = {"en": "English", "ru": "Roman Urdu"}
SYSTEM = (
    "You are a clinical documentation assistant for a physiotherapy clinic. "
    "Write a concise SOAP note in English from the consultation transcript. "
    "Use four headings: Subjective, Objective, Assessment, Plan. "
    "Include only information stated in the transcript."
)


def draft(model: str, transcript: str, timeout: int = 180) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": "Transcript:\n" + transcript}],
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2.5:3b")
    args = ap.parse_args()

    cases: List[Dict[str, Any]] = json.loads((HERE / "data" / "consultations.json").read_text(encoding="utf-8"))
    RES.mkdir(exist_ok=True)
    omissions: List[Dict[str, Any]] = []
    review: List[Dict[str, Any]] = []

    with (RES / "notes.jsonl").open("w", encoding="utf-8") as fh:
        for case in cases:
            for lang in ("en", "ru"):
                note_id = f"{case['id']}-{lang}"
                t0 = time.time()
                note = draft(args.model, case[lang])
                secs = round(time.time() - t0, 1)
                fh.write(json.dumps({"note_id": note_id, "model": args.model, "language": LANG[lang],
                                     "seconds": secs, "note": note}, ensure_ascii=False) + "\n")

                missing = {f["id"] for f in missing_facts(note, case["facts"])}
                for f in case["facts"]:
                    omissions.append({"note_id": note_id, "language": LANG[lang], "fact": f["id"],
                                      "description": f["text"], "critical": f["critical"],
                                      "missing": f["id"] in missing})

                sents = split_sections(note)
                for i, s in enumerate(sents, 1):
                    reason = review_reason(s["section"], sentence_flags(s["sentence"], case[lang], case["denied"]))
                    if reason:
                        review.append({"note_id": note_id, "language": LANG[lang], "sentence_no": i,
                                       "section": s["section"], "sentence": s["sentence"], "auto_flag": reason,
                                       "label": "", "severity": "", "comment": ""})
                print(f"{note_id}: {secs:5.1f}s  sentences={len(sents):2d}  missing facts={len(missing)}  "
                      f"to review={sum(r['note_id'] == note_id for r in review)}")

    for name, rows in (("omissions.csv", omissions), ("review.csv", review)):
        with (RES / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    print(f"\nSaved results/notes.jsonl, results/omissions.csv and results/review.csv ({len(review)} sentences to label)")


if __name__ == "__main__":
    main()
