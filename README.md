# Research Log

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23460406.svg)](https://doi.org/10.5281/zenodo.23460406)

A public log of small, reproducible experiments, run on a MacBook M4 (16 GB).
Each folder has its own research question, code, tests, results from my own run, and honest limitations.

## Agentic AI and language models
| Date | Topic | Folder | Research question |
|---|---|---|---|
| Oct 2026 | ReAct paper follow-up | [`react-roman-urdu/`](react-roman-urdu/) | Does a ~3B local model keep ReAct tool-use accuracy on Roman Urdu vs English, and how stable is it? |
| Oct 2026 | Urdu clinical speech-to-text | [`whisper-urdu-wer/`](whisper-urdu-wer/) | How many words does Whisper (tiny/base/small) get wrong on Urdu clinic conversations, and does it keep the clinical key terms? |
| Oct 2026 | Tool-call self-correction | [`tool-call-self-correction/`](tool-call-self-correction/) | Does schema-validator feedback fix a 3B local model's clinic tool calls, in English and Roman Urdu, and which errors does it miss? |
| Oct 2026 | Validation gates and retries | [`toolguard-agent-benchmark/`](toolguard-agent-benchmark/) | How do a validation gate and bounded retries change task success and tool-call cost as tool failures increase? |
| Oct 2026 | Clinical note hallucinations | [`clinical-note-hallucination/`](clinical-note-hallucination/) | How many key facts does a 3B local model leave out of physiotherapy SOAP notes, how many sentences does it add without support, and is Roman Urdu worse? |
| Oct 2026 | Translate-then-draft for Roman Urdu notes | [`translate-then-draft/`](translate-then-draft/) | Does translating a Roman Urdu consultation into English before drafting keep more facts and the right body part, for qwen2.5:3b and llama3.1:8b? |
| Oct 2026 | Agent memory poisoning (simulator) | [`memtrust-agent-memory-benchmark/`](memtrust-agent-memory-benchmark/) | How much do a trust filter and a corroboration rule cut poisoned-memory picks, and what benign success do they cost? |
| Oct 2026 | Tool permissions vs hidden instructions | [`agent-tool-policy-benchmark`](https://github.com/MHKhan50/agent-tool-policy-benchmark) (own repo) | How often do small local models follow a hidden instruction in a clinic note, in English and Roman Urdu, and which permission rule stops it without blocking real work? |

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
- [Whisper halved its errors on Urdu clinic speech, but not on the medical words](https://masmatixinnovations.co.uk/insights/whisper-urdu-clinic.html)
- [The validator said yes. The refund was still wrong.](https://masmatixinnovations.co.uk/insights/tool-call-self-correction.html)
- [In Roman Urdu, a small AI wrote notes about the wrong body part](https://masmatixinnovations.co.uk/insights/clinical-note-hallucination.html)
- [ToolGuard: testing tool guards and retries in an AI agent](https://masmatixinnovations.co.uk/insights/toolguard-agent-benchmark.html)
- [A planted memory fooled a simple AI agent 74% of the time. A trust filter cut it to 9%.](https://masmatixinnovations.co.uk/insights/memtrust-agent-memory-security.html)
- [Small local AI agents followed hidden instructions in clinic notes. Checking the tool's arguments stopped them.](https://masmatixinnovations.co.uk/insights/agent-tool-policy-clinic.html)

## Reproduce an experiment
```bash
cd <folder>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

## Licence and citation
Code is released under the [MIT licence](LICENSE). Third-party data (OpenAQ and its providers, public trial figures) and models (OpenAI Whisper, MIT licence) keeps its original licence and is credited in each folder. To cite this work, use the DOI [10.5281/zenodo.23460406](https://doi.org/10.5281/zenodo.23460406) (release v0.1.0) or see [CITATION.cff](CITATION.cff).
