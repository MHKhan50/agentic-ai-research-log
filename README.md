# Agentic AI Research Log

A public log of small, reproducible experiments on LLM agents, clinical NLP and local models, run on a MacBook M4 (16 GB).
Each folder has its own research question, code, tests, results from my own run, and honest limitations.

| Date | Topic | Folder | Research question |
|---|---|---|---|
| Oct 2026 | ReAct paper follow-up | [`react-roman-urdu/`](react-roman-urdu/) | Does a ~3B local model keep ReAct tool-use accuracy on Roman Urdu vs English? |

Research gaps I am tracking: [gap-bank.md](gap-bank.md)

## Reproduce an experiment
```bash
cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```
