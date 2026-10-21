"""Run every tool-call task through a local Ollama model with a validator-feedback retry loop.

Attempt 1 is the plain baseline (no feedback). If the validator finds schema
issues, they are sent back with the previous output, up to --max-retries times.
Every attempt is logged to results/attempts.jsonl.

Usage:
    python run.py                          # qwen2.5:3b
    python run.py --models qwen2.5:3b llama3.1:8b
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List

import requests

from validator import FORMATS, TYPE_NAMES, parse_json, schema_issues, value_errors

HERE = Path(__file__).resolve().parent
OLLAMA_URL = "http://localhost:11434/api/chat"
SYSTEM = (
    "You are a tool-calling component in a physiotherapy clinic system. "
    "Reply with ONE JSON object containing exactly the tool's parameters. "
    "No explanation, no code fences."
)


def describe_schema(schema: Dict[str, Dict[str, Any]]) -> str:
    lines = []
    for key, spec in schema.items():
        extra = []
        if "format" in spec:
            extra.append(f"format {FORMATS[spec['format']][1]}")
        if "enum" in spec:
            extra.append("one of " + ", ".join(spec["enum"]))
        if "min" in spec:
            extra.append(f"{spec['min']} to {spec['max']}")
        suffix = f" ({'; '.join(extra)})" if extra else ""
        lines.append(f"- {key}: {TYPE_NAMES[spec['type']]}{suffix}")
    return "\n".join(lines)


def chat(model: str, messages: List[Dict[str, str]], timeout: int = 120) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.0, "seed": 42},
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def run_task(model: str, task: Dict[str, Any], lang: str, max_retries: int) -> List[Dict[str, Any]]:
    user = (
        f"Tool: {task['tool']}\nParameters:\n{describe_schema(task['schema'])}\n\n"
        f"Request: {task['request'][lang]}"
    )
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    rows: List[Dict[str, Any]] = []
    for attempt in range(1, max_retries + 2):
        t0 = time.time()
        raw = chat(model, messages)
        obj, strict_ok = parse_json(raw)
        issues = schema_issues(obj, task["schema"])
        if not strict_ok and obj is not None:
            issues = ["reply was not a bare JSON object (extra text or code fences)"] + issues
        wrong = value_errors(obj, task["expected"])
        rows.append({
            "model": model, "task_id": task["task_id"], "lang": lang, "attempt": attempt,
            "raw": raw, "strict_json": strict_ok, "schema_issues": issues,
            "schema_valid": not issues, "value_errors": wrong, "value_correct": not wrong,
            "seconds": round(time.time() - t0, 2),
        })
        if not issues:
            break
        # Feedback contains only what a validator can know, never the expected values.
        messages += [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": "The tool call was rejected by the validator:\n- "
             + "\n- ".join(issues) + "\nReturn the corrected JSON object only."},
        ]
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen2.5:3b"])
    ap.add_argument("--max-retries", type=int, default=2)
    args = ap.parse_args()

    tasks = json.loads((HERE / "data" / "tasks.json").read_text(encoding="utf-8"))
    out = HERE / "results" / "attempts.jsonl"
    out.parent.mkdir(exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for model in args.models:
            for task in tasks:
                for lang in ("en", "ru"):
                    rows = run_task(model, task, lang, args.max_retries)
                    for r in rows:
                        fh.write(json.dumps(r, ensure_ascii=False) + "\n")
                    last = rows[-1]
                    print(f"{model:14s} {task['task_id']} {lang}  attempts={len(rows)}  "
                          f"schema_ok={last['schema_valid']!s:5s} value_ok={last['value_correct']!s:5s} "
                          f"{last['value_errors'] or ''}")
    print(f"\nSaved {out.relative_to(HERE)}")


if __name__ == "__main__":
    main()
