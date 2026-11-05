"""Run the benchmark on local Ollama models. Resumable: finished calls are skipped.

    python run.py                          # all four models, then commit and push the results
    python run.py --models qwen2.5:3b --limit 4 --no-push   # quick check

Every call is appended to results/runs.jsonl with its full transcript.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agent import ClinicTools, OllamaChat, direct, react, translate_then_react
from bench_items import FORMS, build_items, build_kb
from scoring import score

HERE = Path(__file__).resolve().parent
MODELS = ["qwen2.5:3b", "llama3.2:3b", "qwen2.5:7b", "llama3.1:8b"]  # faster models first
METHODS = {
    "en": ["direct", "react_en_shot"],
    "ru": ["direct", "react_en_shot", "react_ru_shot", "translate_react"],
    "ru_var": ["direct", "react_en_shot", "react_ru_shot", "translate_react"],
}


def plan(items: List[Dict[str, Any]], models: List[str]) -> List[tuple]:
    return [(m, it["id"], form, method) for m in models for it in items for form in FORMS for method in METHODS[form]]


def op_error(expected: Optional[str], exprs: List[str], correct: bool) -> bool:
    """A wrong answer computed without the operator the question needs (e.g. minus for 'baad')."""
    if correct or not expected or not exprs:
        return False
    return not any(expected in e for e in exprs)


def run_one(llm: Callable[..., str], item: Dict[str, Any], form: str, method: str) -> Dict[str, Any]:
    kb = build_kb(item["name_set"])
    tools = ClinicTools(kb).registry()
    q = item[form]
    if method == "direct":
        tr = direct(llm, kb, q)
    elif method == "translate_react":
        tr = translate_then_react(llm, tools, q)
    else:
        tr = react(llm, tools, q, shot="ru" if method == "react_ru_shot" else "en")
    lenient = score(tr.answer, item["gold"])
    return {
        "question": q, "answer": tr.answer, "correct": lenient,
        "correct_strict": score(tr.answer, item["gold"], strict=True),
        "steps": tr.steps, "lookups": tr.lookups, "calc_exprs": tr.calc_exprs,
        "parse_errors": tr.parse_errors, "hit_max_steps": tr.hit_max_steps,
        "op_error": op_error(item["expected_op"], tr.calc_exprs, lenient),
        "skipped_lookup": method != "direct" and tr.lookups < item["required_lookups"],
        "latency_s": round(tr.latency_s, 3), "translation": tr.translation, "transcript": tr.transcript,
    }


def check_ollama(host: str, models: List[str]) -> None:
    import requests
    try:
        names = {m["name"] for m in requests.get(f"{host}/api/tags", timeout=5).json().get("models", [])}
    except requests.RequestException:
        sys.exit(f"Ollama is not reachable at {host}. Open the Ollama app and try again.")
    missing = [m for m in models if m not in names and f"{m}:latest" not in names]
    if missing:
        sys.exit("Model(s) not pulled: " + ", ".join(missing) + ". Run: " + " && ".join(f"ollama pull {m}" for m in missing))


def git_push(paths: List[Path], message: str) -> None:
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=HERE, capture_output=True, text=True)
    if root.returncode != 0:
        print("Not a git repository; results were not pushed.")
        return
    cmds = [["git", "add", *[str(p) for p in paths]], ["git", "commit", "-m", message], ["git", "pull", "--rebase"],
            ["git", "push"]]
    for c in cmds:
        r = subprocess.run(c, cwd=HERE, capture_output=True, text=True)
        print("$ " + " ".join(c) + ("" if r.returncode == 0 else f"\n{r.stdout}{r.stderr}"))
        if r.returncode != 0 and c[1] != "commit":
            print("Push did not finish; run the git commands above by hand.")
            return


def main(argv: Optional[List[str]] = None, chat_factory: Optional[Callable[[str], Callable[..., str]]] = None,
         out_dir: Optional[Path] = None) -> Path:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--limit", type=int, default=None, help="only the first N items (quick check)")
    ap.add_argument("--no-push", action="store_true", help="do not commit and push the results at the end")
    args = ap.parse_args(argv)
    out = out_dir or HERE / "results"
    out.mkdir(parents=True, exist_ok=True)
    path = out / "runs.jsonl"

    items = build_items()[: args.limit] if args.limit else build_items()
    by_id = {it["id"]: it for it in items}
    if chat_factory is None:
        check_ollama(args.host, args.models)
        chat_factory = lambda m: OllamaChat(m, host=args.host)  # noqa: E731

    done = set()
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            done.add((r["model"], r["item_id"], r["form"], r["method"]))
    todo = [k for k in plan(items, args.models) if k not in done]
    total = len(todo) + len(done)
    print(f"{len(done)} calls already done, {len(todo)} to go.", flush=True)

    started, latencies = time.time(), []
    with path.open("a", encoding="utf-8") as fh:
        current, llm = None, None
        for n, (model, item_id, form, method) in enumerate(todo, 1):
            if model != current:
                current, llm = model, chat_factory(model)
            item = by_id[item_id]
            try:
                res = run_one(llm, item, form, method)
            except Exception as exc:  # noqa: BLE001 - log and continue; a rerun retries it
                print(f"failed {model} {item_id} {form} {method}: {exc}", flush=True)
                continue
            rec = {"model": model, "item_id": item_id, "base_id": item["base_id"], "name_set": item["name_set"],
                   "template": item["template"], "form": form, "method": method, **res}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            latencies.append(res["latency_s"])
            if n % 10 == 0 or n == len(todo):
                avg = (time.time() - started) / n
                eta = avg * (len(todo) - n) / 3600
                print(f"{len(done) + n}/{total}  {model:12s} {item_id} {form:6s} {method:15s} "
                      f"{'OK ' if res['correct'] else 'BAD'}  about {eta:.1f} h left", flush=True)

    print(f"Saved {path}")
    if not args.no_push and chat_factory is not None and out_dir is None:
        git_push([path], "Roman Urdu ReAct benchmark: model runs")
    return path


if __name__ == "__main__":
    main()
