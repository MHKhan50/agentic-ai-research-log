# Research Log

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23460406.svg)](https://doi.org/10.5281/zenodo.23460406)

A public log of small, reproducible experiments, run on a MacBook M4 (16 GB).
Each folder has its own research question, code, tests, results from my own run, and honest limitations.

## Agentic AI and language models
| Date | Topic | Folder | Research question |
|---|---|---|---|
| Oct 2026 | ReAct paper follow-up | [`react-roman-urdu/`](react-roman-urdu/) | Does a ~3B local model keep ReAct tool-use accuracy on Roman Urdu vs English, and how stable is it? |

Research gaps I am tracking: [gap-bank.md](gap-bank.md)

## Data, AI and public policy
| Date | Topic | Folder | Research question |
|---|---|---|---|
| Oct 2026 | Air quality, Lahore | [`lahore-smog/`](lahore-smog/) | On what share of days did Lahore's PM2.5 exceed the WHO 24-hour guideline in the last year? |
| Oct 2026 | Air quality, six cities | [`pakistan-cities-air/`](pakistan-cities-air/) | How do six Pakistani cities compare on PM2.5, and which lack open monitoring data? |
| Oct 2026 | AI road-safety cameras, UK | [`uk-ai-road-cameras/`](uk-ai-road-cameras/) | How many AI phone/seatbelt camera flags could be wrong, and how much does human review matter? |

## Articles
Plain-language write-ups of each experiment:
- [Can a small local AI agent understand Roman Urdu?](https://masmatixinnovations.co.uk/insights/react-roman-urdu.html)
- [Lahore did not have a single clean-air day in the past year](https://masmatixinnovations.co.uk/insights/lahore-smog.html)
- [Six Pakistani cities, one year of air](https://masmatixinnovations.co.uk/insights/pakistan-cities-air.html)
- [AI road cameras: how many flags are wrong?](https://masmatixinnovations.co.uk/insights/uk-ai-road-cameras.html)

## Reproduce an experiment
```bash
cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

## Licence and citation
Code is released under the [MIT licence](LICENSE). Third-party data (OpenAQ and its providers, public trial figures) keeps its original licence and is credited in each folder. To cite this work, use the DOI [10.5281/zenodo.23460406](https://doi.org/10.5281/zenodo.23460406) (release v0.1.0) or see [CITATION.cff](CITATION.cff).
