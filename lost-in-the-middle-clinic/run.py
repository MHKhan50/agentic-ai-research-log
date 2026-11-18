"""Ask local models one question per record and save every answer.

Conditions per fact and language:
- closed_book: the question only, no notes (how guessable is the answer?)
- oracle: the gold note only
- pos01, pos08, pos15, pos23, pos30: all 30 notes, gold note at that position

Ollama settings: temperature 0, seed 42, num_ctx 8192 (the default context of
some Ollama versions would silently cut a 30-note record), num_predict 48.
The prompt token count Ollama reports is saved, so a cut prompt is visible.

Writes results/runs.jsonl, one line per answer. Finished keys are skipped, so
the run can be stopped with Ctrl+C and started again.

Usage:
    python run.py                         # both models, both languages
    python run.py --models qwen2.5:3b --facts F01 F02
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple

import records
from score import is_correct

HERE = Path(__file__).resolve().parent
RUNS = HERE / "results" / "runs.jsonl"
OLLAMA = "http://localhost:11434"
MODELS = ("qwen2.5:3b", "llama3.1:8b")
NUM_CTX = 8192
NUM_PREDICT = 48
OPTIONS = {"temperature": 0.0, "seed": 42, "num_ctx": NUM_CTX, "num_predict": NUM_PREDICT}

SYSTEM_NOTES = ("You are a clinic assistant. Answer the question using only the patient's "
                "visit notes. Reply in a few words.")
SYSTEM_CLOSED = "You are a clinic assistant. Answer the question about the patient in a few words."

# chat(model, system, user) -> (answer text, metadata such as prompt_eval_count)
Chat = Callable[[str, str, str], Tuple[str, Dict[str, object]]]
Key = Tuple[str, str, str, str]  # model, lang, fact id, condition


def ollama_chat(model: str, system: str, user: str, timeout: int = 300) -> Tuple[str, Dict[str, object]]:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": OPTIONS,
    }
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    meta = {k: body.get(k) for k in ("prompt_eval_count", "eval_count", "done_reason")}
    return body["message"]["content"], meta


def check_ollama(models: Sequence[str]) -> None:
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=10) as resp:
            have = {m["name"] for m in json.loads(resp.read().decode("utf-8"))["models"]}
    except (urllib.error.URLError, OSError) as exc:
        sys.exit(f"Ollama is not reachable at {OLLAMA} ({exc}). Open the Ollama app and try again.")
    missing = [m for m in models if m not in have and m + ":latest" not in have]
    if missing:
        sys.exit("Missing models: " + ", ".join(missing) + ". Run: ollama pull <model>")


def build_prompt(fact: Dict[str, object], lang: str, condition: str) -> Tuple[str, str]:
    q = records.question(fact, lang)
    if condition == "closed_book":
        return SYSTEM_CLOSED, f"Question: {q}\nAnswer:"
    if condition == "oracle":
        notes = [records.gold_note(fact, lang)]
    else:
        notes = records.build_notes(fact, lang, int(condition[3:]))
    return SYSTEM_NOTES, "Visit notes:\n\n" + "\n\n".join(notes) + f"\n\nQuestion: {q}\nAnswer:"


def plan(models: Sequence[str], langs: Sequence[str], fact_ids: Optional[Sequence[str]]) -> List[Key]:
    facts = [f for f in records.FACTS if not fact_ids or f["id"] in fact_ids]
    # model outermost so Ollama loads each model once
    return [(m, lang, str(f["id"]), c) for m in models for lang in langs
            for f in facts for c in records.conditions()]


def load_done(path: Path) -> set:
    done = set()
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    done.add((r["model"], r["lang"], r["fact"], r["condition"]))
    return done


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m // 60}h{m % 60:02d}m" if m >= 60 else f"{m}m{s:02d}s"


def run(keys: Sequence[Key], chat: Chat, out: Path, log: Callable[[str], None] = print) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out)
    todo = [k for k in keys if k not in done]
    facts = {str(f["id"]): f for f in records.FACTS}
    log(f"{len(keys) - len(todo)} already done, {len(todo)} to run")
    start = time.time()
    with out.open("a", encoding="utf-8") as fh:
        for i, (model, lang, fid, cond) in enumerate(todo, start=1):
            fact = facts[fid]
            system, user = build_prompt(fact, lang, cond)
            t0 = time.time()
            answer, meta = chat(model, system, user)
            prompt_tokens = meta.get("prompt_eval_count")
            row = {
                "model": model, "lang": lang, "fact": fid, "condition": cond,
                "answer": answer.strip(),
                "correct": is_correct(answer, fact["accept"]),  # type: ignore[arg-type]
                "prompt_tokens": prompt_tokens,
                "answer_tokens": meta.get("eval_count"),
                "possibly_cut": bool(prompt_tokens and int(prompt_tokens) >= NUM_CTX - NUM_PREDICT),
                "seconds": round(time.time() - t0, 2),
                "options": OPTIONS,
            }
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            rate = (time.time() - start) / i
            log(f"[{i}/{len(todo)}] {model} {lang} {fid} {cond} "
                f"{'OK ' if row['correct'] else 'MISS'} eta {_fmt(rate * (len(todo) - i))}")
    return len(todo)


def main(argv: Optional[Sequence[str]] = None, chat: Optional[Chat] = None, out: Path = RUNS) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", nargs="+", default=list(MODELS))
    ap.add_argument("--langs", nargs="+", default=list(records.LANGS), choices=records.LANGS)
    ap.add_argument("--facts", nargs="+", default=None)
    args = ap.parse_args(argv)
    if chat is None:
        check_ollama(args.models)
        chat = ollama_chat
    return run(plan(args.models, args.langs, args.facts), chat, out)


if __name__ == "__main__":
    main()
