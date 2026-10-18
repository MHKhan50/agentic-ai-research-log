# Research Log

A public log of small, reproducible experiments, run on a MacBook M4 (16 GB).
Each folder has its own research question, code, tests, results from my own run, and honest limitations.

## Agentic AI and language models
| Date | Topic | Folder | Research question |
|---|---|---|---|
| Oct 2026 | ReAct paper follow-up | [`react-roman-urdu/`](react-roman-urdu/) | Does a ~3B local model keep ReAct tool-use accuracy on Roman Urdu vs English, and how stable is it? |

Research gaps I am tracking: [gap-bank.md](gap-bank.md)

## Data and public health
| Date | Topic | Folder | Research question |
|---|---|---|---|
| Oct 2026 | Air quality, Lahore | [`lahore-smog/`](lahore-smog/) | On what share of days did Lahore's PM2.5 exceed the WHO 24-hour guideline in the last year? |
| Oct 2026 | Air quality, six cities | [`pakistan-cities-air/`](pakistan-cities-air/) | How do six Pakistani cities compare on PM2.5, and which lack open monitoring data? |

## Reproduce an experiment
```bash
cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```
