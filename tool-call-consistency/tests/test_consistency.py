"""Offline tests: estimator, job grid, resume, and an end-to-end run with a scripted fake LLM."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

import pytest

import analysis
import run
from consistency import N_TRIALS, build_jobs, done_keys, load_tasks, pass_hat_k


def test_pass_hat_k_values():
    assert pass_hat_k(5, 5, 5) == 1.0
    assert pass_hat_k(5, 4, 5) == 0.0
    assert pass_hat_k(5, 3, 1) == pytest.approx(0.6)
    assert pass_hat_k(5, 4, 2) == pytest.approx(6 / 10)
    with pytest.raises(ValueError):
        pass_hat_k(5, 5, 6)


def test_tasks_have_five_phrasings_and_unique_wordings():
    tasks = load_tasks()
    assert len(tasks) == 8
    for t in tasks:
        for lang in ("en", "ru"):
            ph = t["phrasings"][lang]
            assert len(ph) == N_TRIALS and len(set(ph)) == N_TRIALS


def test_job_grid():
    jobs = build_jobs(load_tasks(), ["a", "b"])
    assert len(jobs) == 2 * 8 * 2 * 2 * N_TRIALS
    wording = [j for j in jobs if j["condition"] == "wording"]
    sampling = [j for j in jobs if j["condition"] == "sampling"]
    assert all(j["temperature"] == 0.0 and j["seed"] == 42 for j in wording)
    assert {j["seed"] for j in sampling} == set(range(1, N_TRIALS + 1))
    assert len({j["request"] for j in sampling if j["task_id"] == "T01" and j["lang"] == "ru"}) == 1


def make_fake_chat():
    """Correct JSON, except: Roman Urdu wording trial 2 gets a wrong value, and
    sampling seed 3 wraps the answer in a code fence with a wrong pulse."""
    tasks = {t["tool"]: t for t in load_tasks()}

    def chat(model: str, messages: List[Dict[str, str]], temperature: float, seed: int) -> str:
        tool = messages[1]["content"].split("\n", 1)[0].replace("Tool: ", "")
        obj = dict(tasks[tool]["expected"])
        request = messages[1]["content"].rsplit("Request: ", 1)[1]
        if temperature == 0.0 and request == tasks[tool]["phrasings"]["ru"][2]:
            key = next(iter(obj))  # first key is an id (int or str) in every task
            obj[key] = obj[key] + 1 if isinstance(obj[key], int) else obj[key] + "9"
        if seed == 3 and tool == "record_vitals":
            obj["pulse"] = 27
            return "```json\n" + json.dumps(obj) + "\n```"
        return json.dumps(obj)
    return chat


def test_end_to_end_mock_run_and_resume(tmp_path: Path):
    out = tmp_path / "runs.jsonl"
    n = run.main(["--models", "fake:1b"], chat=make_fake_chat(), out=out)
    assert n == 8 * 2 * 2 * N_TRIALS
    assert len(done_keys(out)) == n
    assert run.main(["--models", "fake:1b"], chat=make_fake_chat(), out=out) == 0  # resume skips all

    summary = analysis.main(results_dir=tmp_path)
    by = {(r["language"], r["condition"]): r for r in summary}
    assert by[("English", "wording")]["pass^5"] == 1.0
    ru_w = by[("Roman Urdu", "wording")]
    assert ru_w["pass^1"] == pytest.approx(0.8) and ru_w["pass^5"] == 0.0
    assert ru_w["mixed"] == 8
    en_s = by[("English", "sampling")]
    assert en_s["mixed"] == 1 and en_s["pass^5"] == pytest.approx(7 / 8)
    assert (tmp_path / "pass_k.png").stat().st_size > 10_000
    data = json.loads((tmp_path / "results.json").read_text())
    assert len(data["task_outcomes"]) == 8 * 2 * 2


def test_half_written_line_is_ignored(tmp_path: Path):
    out = tmp_path / "runs.jsonl"
    out.write_text('{"key": "a"}\n{"key": "b', encoding="utf-8")
    assert done_keys(out) == {"a"}


def test_timeout_is_retried_once_then_recorded_as_failed(tmp_path: Path):
    import requests
    calls = {"n": 0}

    def slow_chat(model, messages, temperature, seed):
        calls["n"] += 1
        raise requests.Timeout()

    out = tmp_path / "runs.jsonl"
    guarded = run.with_timeout_guard(slow_chat)
    assert guarded("m", [], 0.0, 42) == run.TIMEOUT_REPLY and calls["n"] == 2
    rows_before = calls["n"]
    run.main(["--models", "fake:1b"], chat=slow_chat, out=out)
    rows = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(rows) == 8 * 2 * 2 * N_TRIALS and not any(r["passed"] for r in rows)
    assert calls["n"] - rows_before == 2 * len(rows)
