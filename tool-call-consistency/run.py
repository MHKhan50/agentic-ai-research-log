"""Resumable runner: every task x language x condition x trial for each model.

Results go to results/runs.jsonl, one line per call. Finished keys are skipped,
so the run can be stopped (Ctrl+C) and started again.

Usage:
    python run.py                                  # qwen2.5:3b and llama3.1:8b
    python run.py --models qwen2.5:3b
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Dict, List

import requests

from consistency import HERE, build_jobs, done_keys, job_key, load_tasks, run_job

OLLAMA_URL = "http://localhost:11434/api/chat"
# A tool call is a short JSON object. The cap stops a model that keeps
# generating (a repetition loop) from blocking the run; such a reply fails.
MAX_TOKENS = 256
TIMEOUT_S = 120
TIMEOUT_REPLY = "<timeout>"


def ollama_chat(model: str, messages: List[Dict[str, str]], temperature: float, seed: int) -> str:
    payload = {"model": model, "messages": messages, "stream": False, "keep_alive": "30m",
               "options": {"temperature": temperature, "seed": seed, "num_predict": MAX_TOKENS}}
    resp = requests.post(OLLAMA_URL, json=payload, timeout=TIMEOUT_S)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def with_timeout_guard(chat):
    """Retry a timed-out call once; if it times out again, record it as a failed call."""
    def guarded(model: str, messages: List[Dict[str, str]], temperature: float, seed: int) -> str:
        for _ in range(2):
            try:
                return chat(model, messages, temperature, seed)
            except requests.Timeout:
                print("  call timed out, retrying once" if _ == 0 else "  timed out again, recorded as failed")
        return TIMEOUT_REPLY
    return guarded


def main(argv=None, chat=ollama_chat, out: Path = HERE / "results" / "runs.jsonl") -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=["qwen2.5:3b", "llama3.1:8b"])
    args = ap.parse_args(argv)

    tasks = {t["task_id"]: t for t in load_tasks()}
    jobs = build_jobs(list(tasks.values()), args.models)
    out.parent.mkdir(parents=True, exist_ok=True)
    finished = done_keys(out)
    todo = [j for j in jobs if job_key(j) not in finished]
    print(f"{len(jobs)} calls in total, {len(jobs) - len(todo)} already done, {len(todo)} to run")
    guarded_chat = with_timeout_guard(chat)
    t0 = time.time()
    with out.open("a", encoding="utf-8") as fh:
        for i, job in enumerate(todo, 1):
            row = run_job(job, tasks[job["task_id"]], guarded_chat)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            avg = (time.time() - t0) / i
            eta = avg * (len(todo) - i) / 60
            print(f"[{i}/{len(todo)}] {row['key']:42s} pass={row['passed']!s:5s} "
                  f"{','.join(row['value_errors']) or ''}  ETA {eta:.1f} min")
    print(f"Saved {out}. Next: python analysis.py")
    return len(todo)


if __name__ == "__main__":
    main()
