"""Give a small local omission judge a third label: present, missing or contradicted.

The local omission judge (../llm-omission-judge/) could only say "present" or
"missing". A fact written wrongly, such as "left knee" for a right knee or
"no swelling" when the knee swelled, has no label of its own there (gap G12).
This script asks qwen2.5:3b and llama3.1:8b to judge the same notes twice:

- binary:  the prompt from ../llm-omission-judge/ (present / missing)
- three:   the same task with a third answer, "contradicted"

Notes (200, none drafted here):
- 80 notes from ../roman-urdu-soap-benchmark/ (20 cases x English/Roman Urdu x 2 models)
- 120 Roman Urdu notes from ../injured-side-rule/ (rule, rule + glossary, retry x 2 models x 20)

Facts: the case facts I wrote, plus one "injured area" fact per case built from
the case's body region and side (cases C2 and C3 already list it as "side").

Results go to results/runs.jsonl, one line per judge call. The runner skips
keys that are already done, so it can be stopped and started again.

Usage:
    python contradiction_judge.py                     # 800 calls, both judges, both prompts
    python contradiction_judge.py --limit 3           # quick check on 3 notes
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BENCH = ROOT / "roman-urdu-soap-benchmark"
sys.path.insert(0, str(BENCH))
import run as bench  # noqa: E402

RES = HERE / "results"
RUNS = RES / "runs.jsonl"
BENCH_NOTES = BENCH / "results" / "notes.jsonl"
RULE_NOTES = ROOT / "injured-side-rule" / "results" / "notes.jsonl"
RULE_CONDITIONS = ("rule", "rule_glossary", "retry")
JUDGES = ("qwen2.5:3b", "llama3.1:8b")
PROMPTS = ("binary", "three")
LABELS = ("present", "missing", "contradicted")
OLLAMA_URL = "http://localhost:11434/api/chat"

Chat = Callable[[str, str, str], str]

# The binary prompt is the one used in ../llm-omission-judge/judge.py, word for word.
SYSTEM: Dict[str, str] = {
    "binary": (
        "You check clinical notes for omissions. You get a SOAP note and a numbered list of facts "
        "from the consultation. For each fact, answer \"present\" if the note states it (any wording, "
        "any language), or \"missing\" if the note leaves it out completely or partly. "
        "Reply with JSON only, for example {\"1\": \"present\", \"2\": \"missing\"}."
    ),
    "three": (
        "You check clinical notes for omissions and errors. You get a SOAP note and a numbered list "
        "of facts from the consultation. For each fact, answer \"present\" if the note states it "
        "correctly (any wording, any language), \"missing\" if the note leaves it out completely or "
        "partly, or \"contradicted\" if the note states something that conflicts with it, for example "
        "the other side, a different body part, a different number or dose, or absent when it was "
        "present. Reply with JSON only, for example "
        "{\"1\": \"present\", \"2\": \"missing\", \"3\": \"contradicted\"}."
    ),
}

AREA_TEXT: Dict[str, str] = {
    "back": "back", "neck": "neck", "shoulder": "shoulder", "knee": "knee",
    "hip/groin": "hip or groin", "ankle/foot": "ankle or foot", "wrist/hand": "wrist or hand",
    "elbow": "elbow", "leg": "leg", "arm": "arm", "head": "head", "chest": "chest",
}


def area_fact(case: Dict[str, Any]) -> Dict[str, Any]:
    """The injured area as a fact: 'right knee', or 'back' when the case has no side."""
    text = AREA_TEXT[case["main_region"]]
    if case.get("side"):
        text = f"{case['side']} {text}"
    return {"id": "injured_area", "text": f"injured area: {text}", "critical": True}


def facts_for(case: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Case facts plus the injured-area fact, unless the case already lists the side as a fact."""
    facts = list(case["facts"])
    if not any(f["id"] == "side" for f in facts):
        facts.append(area_fact(case))
    return facts


def build_user(note: str, facts: Sequence[Dict[str, Any]]) -> str:
    lines = [f"{i}. {f['id'].replace('_', ' ')}: {f['text']}" for i, f in enumerate(facts, 1)]
    return "SOAP note:\n" + note + "\n\nFacts:\n" + "\n".join(lines)


def parse_reply(reply: str, n: int, prompt: str) -> Optional[Dict[int, str]]:
    """Map fact number -> label. None if the JSON is missing, broken or incomplete.
    In the binary prompt any word other than 'missing' counts as present, as in the earlier run."""
    m = re.search(r"\{.*\}", reply, flags=re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    out: Dict[int, str] = {}
    for k, v in obj.items():
        num = re.sub(r"\D", "", str(k))
        if not num or not 1 <= int(num) <= n:
            continue
        word = str(v).lower()
        if prompt == "three" and "contradict" in word:
            out[int(num)] = "contradicted"
        elif "miss" in word:
            out[int(num)] = "missing"
        elif prompt == "three" and "present" not in word:
            return None  # an unknown label in the three-label prompt is a parse failure
        else:
            out[int(num)] = "present"
    return out if len(out) == n else None


def load_notes(bench_path: Path = BENCH_NOTES, rule_path: Path = RULE_NOTES) -> List[Dict[str, Any]]:
    """The 200 notes, each with a stable key."""
    notes: List[Dict[str, Any]] = []
    for line in bench_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            notes.append({"key": f"bench|{r['model']}|{r['lang']}|baseline|{r['case']}",
                          "model": r["model"], "lang": r["lang"], "condition": "baseline",
                          "case": r["case"], "note": r["note"]})
    for line in rule_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["condition"] in RULE_CONDITIONS:
                notes.append({"key": f"rule|{r['model']}|ru|{r['condition']}|{r['case']}",
                              "model": r["model"], "lang": "ru", "condition": r["condition"],
                              "case": r["case"], "note": r["note"]})
    return notes


def ollama_chat(model: str, system: str, user: str, timeout: int = 300) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42, "num_predict": 400},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    return str(resp.json()["message"]["content"])


def judge_once(chat: Chat, judge: str, prompt: str, note: Dict[str, Any],
               facts: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """One judge call with one retry for unusable JSON. Returns the record for runs.jsonl."""
    user = build_user(note["note"], facts)
    t0 = time.time()
    reply, error = "", ""
    parsed: Optional[Dict[int, str]] = None
    for attempt in (user, user + "\n\nAnswer with the JSON object only."):
        try:
            reply = chat(judge, SYSTEM[prompt], attempt)
        except Exception as exc:  # timeout or connection error: record it, keep going
            error = f"{type(exc).__name__}: {exc}"[:200]
            continue
        parsed = parse_reply(reply, len(facts), prompt)
        if parsed is not None:
            break
    return {
        "key": note["key"], "judge": judge, "prompt": prompt, "model": note["model"],
        "lang": note["lang"], "condition": note["condition"], "case": note["case"],
        "facts": [f["id"] for f in facts],
        "labels": None if parsed is None else [parsed[i] for i in range(1, len(facts) + 1)],
        "parse_ok": parsed is not None, "error": error, "reply": reply[:2000],
        "seconds": round(time.time() - t0, 1),
    }


def done_keys(path: Path) -> set:
    """Keys already judged with a parsed reply; failed calls are tried again on the next start."""
    keys = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if r.get("parse_ok"):
                    keys.add((r["judge"], r["prompt"], r["key"]))
    return keys


def main(chat: Chat = ollama_chat, argv: Optional[List[str]] = None, runs: Path = RUNS) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--judges", nargs="+", default=list(JUDGES))
    ap.add_argument("--prompts", nargs="+", default=list(PROMPTS), choices=PROMPTS)
    ap.add_argument("--limit", type=int, default=None, help="only the first N notes (quick check)")
    args = ap.parse_args(argv)

    cases = {c["id"]: c for c in bench.load_cases()}
    notes = load_notes()[: args.limit]
    done = done_keys(runs)
    todo = [(j, p, n) for j in args.judges for p in args.prompts for n in notes
            if (j, p, n["key"]) not in done]
    print(f"{len(notes)} notes x {len(args.judges)} judges x {len(args.prompts)} prompts: "
          f"{len(todo)} calls to do, {len(done)} already done")
    runs.parent.mkdir(parents=True, exist_ok=True)
    t_start, failed = time.time(), 0
    for i, (judge, prompt, note) in enumerate(todo, 1):
        rec = judge_once(chat, judge, prompt, note, facts_for(cases[note["case"]]))
        with runs.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        failed += not rec["parse_ok"]
        avg = (time.time() - t_start) / i
        eta = avg * (len(todo) - i) / 60
        counts = {lab: (rec["labels"] or []).count(lab) for lab in LABELS}
        print(f"[{i}/{len(todo)}] {judge:12s} {prompt:6s} {note['key']:36s} {rec['seconds']:5.1f}s "
              f"P{counts['present']:2d} M{counts['missing']:2d} C{counts['contradicted']:2d}"
              f"{'  FAILED ' + rec['error'][:60] if not rec['parse_ok'] else ''}  ETA {eta:5.1f} min",
              flush=True)
    print(f"\nDone. {failed} calls without usable JSON (start the script again to retry them).")
    print("Next: python analysis.py")
    return failed


def check_ollama(judges: Sequence[str] = JUDGES) -> None:
    """Stop early with a clear message if Ollama is closed or a judge model is not pulled."""
    try:
        tags = requests.get("http://localhost:11434/api/tags", timeout=5).json()
    except requests.exceptions.RequestException:
        sys.exit("Cannot reach Ollama at localhost:11434. Open the Ollama app, then run this again.")
    have = {m.get("name", "") for m in tags.get("models", [])}
    lost = [j for j in judges if j not in have and f"{j}:latest" not in have]
    if lost:
        sys.exit("Missing models: " + ", ".join(lost) + ". Run: ollama pull " + " && ollama pull ".join(lost))


if __name__ == "__main__":
    check_ollama()
    main()
