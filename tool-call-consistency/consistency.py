"""Core logic for the tool-call consistency test (no network, no model).

Two ways to repeat the same tool call five times:

* ``wording``: five phrasings of the same request, temperature 0, seed 42.
  Only the words change, so any change in the output comes from wording.
* ``sampling``: the original phrasing, temperature 0.7, seeds 1 to 5.
  Only the random sampling changes.

A task passes in a trial when the JSON is schema valid and every value is
right. pass^k (Yao et al. 2024, tau-bench) is the chance that k trials of the
same task all pass, estimated as mean over tasks of C(c, k) / C(n, k).
"""
from __future__ import annotations

import json
import sys
import time
from math import comb
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "tool-call-self-correction"
sys.path.append(str(BASE))  # appended, so this folder's run.py is never shadowed

from validator import FORMATS, TYPE_NAMES, parse_json, schema_issues, value_errors  # noqa: E402

LANGS = ("en", "ru")
N_TRIALS = 5
SAMPLING_TEMPERATURE = 0.7
# Same system prompt as tool-call-self-correction, so the two folders are comparable.
SYSTEM = (
    "You are a tool-calling component in a physiotherapy clinic system. "
    "Reply with ONE JSON object containing exactly the tool's parameters. "
    "No explanation, no code fences."
)

ChatFn = Callable[[str, List[Dict[str, str]], float, int], str]


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


def load_tasks(base: Path = BASE, here: Path = HERE) -> List[Dict[str, Any]]:
    """Tasks from the earlier folder, each with five phrasings per language."""
    tasks = json.loads((base / "data" / "tasks.json").read_text(encoding="utf-8"))
    variants = json.loads((here / "data" / "variants.json").read_text(encoding="utf-8"))
    for t in tasks:
        t["phrasings"] = {
            lang: [t["request"][lang]] + list(variants[t["task_id"]][lang]) for lang in LANGS
        }
        for lang in LANGS:
            if len(t["phrasings"][lang]) != N_TRIALS:
                raise ValueError(f"{t['task_id']} {lang}: need {N_TRIALS} phrasings")
    return tasks


def job_key(job: Dict[str, Any]) -> str:
    return "|".join([job["model"], job["condition"], job["task_id"], job["lang"], str(job["trial"])])


def build_jobs(tasks: List[Dict[str, Any]], models: Iterable[str]) -> List[Dict[str, Any]]:
    jobs: List[Dict[str, Any]] = []
    for model in models:
        for t in tasks:
            for lang in LANGS:
                for trial in range(N_TRIALS):
                    jobs.append({"model": model, "condition": "wording", "task_id": t["task_id"],
                                 "lang": lang, "trial": trial, "temperature": 0.0, "seed": 42,
                                 "request": t["phrasings"][lang][trial]})
                    jobs.append({"model": model, "condition": "sampling", "task_id": t["task_id"],
                                 "lang": lang, "trial": trial, "temperature": SAMPLING_TEMPERATURE,
                                 "seed": trial + 1, "request": t["phrasings"][lang][0]})
    return jobs


def run_job(job: Dict[str, Any], task: Dict[str, Any], chat: ChatFn) -> Dict[str, Any]:
    user = (f"Tool: {task['tool']}\nParameters:\n{describe_schema(task['schema'])}\n\n"
            f"Request: {job['request']}")
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    t0 = time.time()
    raw = chat(job["model"], messages, job["temperature"], job["seed"])
    obj, strict_ok = parse_json(raw)
    issues = schema_issues(obj, task["schema"])
    wrong = value_errors(obj, task["expected"])
    row = dict(job)
    row.update({"key": job_key(job), "raw": raw, "parsed": obj, "strict_json": strict_ok,
                "schema_valid": not issues, "schema_issues": issues, "value_errors": wrong,
                "passed": (not issues) and (not wrong), "seconds": round(time.time() - t0, 2)})
    return row


def done_keys(path: Path) -> set:
    if not path.exists():
        return set()
    keys = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                keys.add(json.loads(line)["key"])
            except (ValueError, KeyError):
                continue  # a half-written last line from an interrupted run
    return keys


def pass_hat_k(n: int, c: int, k: int) -> float:
    """Unbiased estimate that k of n i.i.d. trials all pass, given c passes."""
    if k > n:
        raise ValueError("k cannot exceed n")
    return comb(c, k) / comb(n, k)


def canonical_output(parsed: Optional[Dict[str, Any]]) -> str:
    return json.dumps(parsed, sort_keys=True, ensure_ascii=False) if parsed is not None else "<no json>"
