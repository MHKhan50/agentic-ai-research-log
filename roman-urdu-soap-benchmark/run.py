"""Draft SOAP notes for 20 physiotherapy consultations in English and Roman Urdu.

Cases: the 4 pilot consultations in ../clinical-note-hallucination/data/ plus
16 new ones in data/consultations.json (same format, with main body region and
injured side). Each case is drafted from the English and from the Roman Urdu
transcript with the same prompt as the pilot, by each model.

Writes results/notes.jsonl, results/per_note.csv and results/facts.csv.

Usage:
    python run.py                                   # qwen2.5:3b and llama3.1:8b, all 20 cases
    python run.py --models llama3.1:8b --cases C5 C6
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests

from checks import check_note, missing_by_fact

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "clinical-note-hallucination" / "data" / "consultations.json"
RES = HERE / "results"
OLLAMA_URL = "http://localhost:11434/api/chat"
# Same prompt as clinical-note-hallucination/ and translate-then-draft/.
NOTE_PROMPT = (
    "You are a clinical documentation assistant for a physiotherapy clinic. "
    "Write a concise SOAP note in English from the consultation transcript. "
    "Use four headings: Subjective, Objective, Assessment, Plan. "
    "Include only information stated in the transcript."
)
PILOT_META = {"C1": ("back", None), "C2": ("knee", "right"), "C3": ("shoulder", "left"), "C4": ("neck", None)}
LANGS = ("en", "ru")

Chat = Callable[[str, str, str], str]


def ollama_chat(model: str, system: str, user: str, timeout: int = 300) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def load_cases(pilot: Path = PILOT, new: Path = HERE / "data" / "consultations.json") -> List[Dict[str, Any]]:
    cases = json.loads(pilot.read_text(encoding="utf-8"))
    for c in cases:
        c["main_region"], c["side"] = PILOT_META[c["id"]]
    return cases + json.loads(new.read_text(encoding="utf-8"))


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(chat: Chat = ollama_chat, argv: Optional[List[str]] = None, out: Path = RES) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen2.5:3b", "llama3.1:8b"])
    ap.add_argument("--cases", nargs="+", default=None)
    args = ap.parse_args(argv)
    cases = [c for c in load_cases() if not args.cases or c["id"] in args.cases]
    out.mkdir(exist_ok=True)
    per_note: List[Dict[str, Any]] = []
    facts: List[Dict[str, Any]] = []
    with (out / "notes.jsonl").open("w", encoding="utf-8") as fh:
        for model in args.models:
            for case in cases:
                for lang in LANGS:
                    t0 = time.time()
                    note = chat(model, NOTE_PROMPT, "Transcript:\n" + case[lang])
                    rec = {"note_id": f"{case['id']}-{lang}", "case": case["id"], "model": model, "lang": lang,
                           "seconds": round(time.time() - t0, 1), "note": note}
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                    res = check_note(note, case)
                    per_note.append({"model": model, "case": case["id"], "lang": lang,
                                     "seconds": rec["seconds"], **res, "my_label": "", "my_comment": ""})
                    crit = {f["id"]: f["critical"] for f in case["facts"]}
                    for fid, gone in missing_by_fact(note, case["facts"]).items():
                        facts.append({"model": model, "case": case["id"], "fact": fid,
                                      "critical": crit[fid], "lang": lang, "missing": gone})
                    print(f"{model:12s} {rec['note_id']:7s} {rec['seconds']:5.1f}s  missing={res['facts_missing']:2d}"
                          f"  critical={res['critical_missing']}  region={'ok' if res['main_region_present'] else 'NO'}"
                          f"  side={'WRONG' if res['wrong_side'] else 'ok'}  gate={'REVIEW' if res['gate_flag'] else '-'}")
    write_csv(out / "per_note.csv", per_note)
    write_csv(out / "facts.csv", facts)
    print(f"\nSaved {len(per_note)} notes to results/. Next: python summarise.py")


if __name__ == "__main__":
    main()
