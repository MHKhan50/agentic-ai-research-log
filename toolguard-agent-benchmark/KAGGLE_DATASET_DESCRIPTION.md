# Kaggle dataset listing draft

**Suggested title:** ToolGuard: Synthetic Tool-Using Agent Reliability Benchmark
**Subtitle:** 120 synthetic ticket-triage tasks and reproducible policy-evaluation outputs
**Tags:** `artificial-intelligence`, `agentic-ai`, `synthetic-data`, `reproducibility`, `evaluation`

## Description

ToolGuard is a small, fully synthetic benchmark for studying how validation gates, prerequisite checks, and bounded retries affect a tool-using agent workflow. The core release includes 120 synthetic ticket-triage tasks, 1,440 episode-level results from four scripted policies under three transient tool-failure rates, aggregate metrics, run metadata, and SVG figures.

This dataset is designed for teaching, dissertation prototypes, and reproducibility experiments. It contains no real customer data. The default experiment uses a scripted planner to isolate execution-control mechanisms; it is **not** a leaderboard of LLM reasoning and must not be interpreted as production reliability evidence. The optional Ollama model experiment is separate.

## Files

- `data/tasks.csv`: generated synthetic tasks and target labels.
- `outputs/results.csv`: one row per task/policy/failure-rate condition.
- `outputs/summary.csv`: aggregate metrics.
- `outputs/run_metadata.json`: seed, parameters, Python version, and limitations.
- `outputs/figures/*.svg`: generated plots.
- `docs/article_draft.md` and `docs/article_draft.pdf`: draft methods/results write-up; verify the run before reuse.

## Licence and provenance

The synthetic dataset is released under CC0 1.0. The code is licensed under MIT. Tasks are generated locally by the included script; no third-party data source is used. See `DATA_LICENSE.txt`, `LICENSE`, and `README.md`.

## Suggested citation

ToolGuard synthetic ticket-triage benchmark, version 0.1.0 (2026), generated with the accompanying code and fixed seed. Replace this suggested citation with a versioned repository/archive citation after publication. Do not invent or use a DOI until a repository record actually issues one.
