"""Direct drafting vs translate-then-draft for Roman Urdu consultations.

For each model and consultation, three conditions:
  en-direct      English transcript -> SOAP note (reference)
  ru-direct      Roman Urdu transcript -> SOAP note
  ru-translate   Roman Urdu -> English translation -> SOAP note (same model)

Reuses the consultations, fact patterns and note prompt from
../clinical-note-hallucination/ so the numbers are comparable.

Writes results/notes.jsonl, results/omissions.csv and results/body_regions.csv.

Usage:
    python run.py                         # qwen2.5:3b and llama3.1:8b
    python run.py --models qwen2.5:3b
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List

import requests

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "clinical-note-hallucination"
sys.path.append(str(BASE))

from note_checks import missing_facts  # noqa: E402

from body_checks import region_errors  # noqa: E402

RES = HERE / "results"
OLLAMA_URL = "http://localhost:11434/api/chat"
MAIN_REGION = {"C1": "back", "C2": "knee", "C3": "shoulder", "C4": "neck"}
NOTE_PROMPT = (
    "You are a clinical documentation assistant for a physiotherapy clinic. "
    "Write a concise SOAP note in English from the consultation transcript. "
    "Use four headings: Subjective, Objective, Assessment, Plan. "
    "Include only information stated in the transcript."
)
TRANSLATE_PROMPT = (
    "Translate this physiotherapy consultation from Roman Urdu into English. "
    "Keep the speaker labels and one line per turn. Keep every number, body part, "
    "medicine and every 'no' or 'not' exactly. Do not summarise, add or explain anything. "
    "Output only the translation."
)
CONDITIONS = ("en-direct", "ru-direct", "ru-translate")

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


def run_case(chat: Chat, model: str, case: Dict[str, Any], cond: str) -> Dict[str, Any]:
    t0 = time.time()
    translation = ""
    if cond == "en-direct":
        source = case["en"]
    elif cond == "ru-direct":
        source = case["ru"]
    else:
        translation = chat(model, TRANSLATE_PROMPT, case["ru"])
        source = translation
    note = chat(model, NOTE_PROMPT, "Transcript:\n" + source)
    return {"note_id": f"{case['id']}-{cond}", "case": case["id"], "model": model, "condition": cond,
            "seconds": round(time.time() - t0, 1), "translation": translation, "note": note}


def evaluate(rec: Dict[str, Any], case: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    missing = {f["id"] for f in missing_facts(rec["note"], case["facts"])}
    lost_in_translation = ({f["id"] for f in missing_facts(rec["translation"], case["facts"])}
                           if rec["translation"] else set())
    om = [{"model": rec["model"], "condition": rec["condition"], "note_id": rec["note_id"], "fact": f["id"],
           "critical": f["critical"], "missing": f["id"] in missing,
           "missing_in_translation": (f["id"] in lost_in_translation) if rec["translation"] else ""}
          for f in case["facts"]]
    reg = region_errors(rec["note"], case["en"], MAIN_REGION[case["id"]])
    body = [{"model": rec["model"], "condition": rec["condition"], "note_id": rec["note_id"],
             "main_region": MAIN_REGION[case["id"]], "main_region_present": reg["main_region_present"],
             "unsupported_regions": "; ".join(reg["unsupported_regions"]),
             "label": "", "comment": ""}]
    return {"omissions": om, "body": body}


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main(chat: Chat = ollama_chat, argv: List[str] = None) -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen2.5:3b", "llama3.1:8b"])
    args = ap.parse_args(argv)
    cases = json.loads((BASE / "data" / "consultations.json").read_text(encoding="utf-8"))
    RES.mkdir(exist_ok=True)
    omissions: List[Dict[str, Any]] = []
    body: List[Dict[str, Any]] = []
    with (RES / "notes.jsonl").open("w", encoding="utf-8") as fh:
        for model in args.models:
            for case in cases:
                for cond in CONDITIONS:
                    rec = run_case(chat, model, case, cond)
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    fh.flush()
                    ev = evaluate(rec, case)
                    omissions += ev["omissions"]
                    body += ev["body"]
                    b = ev["body"][0]
                    print(f"{model:12s} {rec['note_id']:16s} {rec['seconds']:6.1f}s  "
                          f"missing={sum(r['missing'] for r in ev['omissions']):2d}  "
                          f"main region={'yes' if b['main_region_present'] else 'NO '}  "
                          f"other regions={b['unsupported_regions'] or '-'}")
    write_csv(RES / "omissions.csv", omissions)
    write_csv(RES / "body_regions.csv", body)
    print("\nSaved results/notes.jsonl, results/omissions.csv, results/body_regions.csv")
    print("Next: python summarise.py")


if __name__ == "__main__":
    main()
