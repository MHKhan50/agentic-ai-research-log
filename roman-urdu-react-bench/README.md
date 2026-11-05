# Roman Urdu ReAct benchmark

A follow-up to the 12-question pilot in [`react-roman-urdu/`](../react-roman-urdu/), where changing only the
names moved a small local ReAct agent's Roman Urdu accuracy from 83% to 58% and the errors came from words such as
"saal baad" (in N years) and "mila kar" (combined). This benchmark repeats the question at a size that supports
confidence intervals.

## Research questions
1. Do small local models answer clinic questions less accurately in Roman Urdu than in English, with ReAct and
   with the whole database in the prompt?
2. Which question types (time words, combining, differences, two-hop lookups) cause the gap?
3. How much do surface changes move accuracy: other names with the same numbers, and chat spelling
   ("kitnay", "baki", "ziada") instead of common spelling?
4. Do two cheap fixes help: a Roman Urdu worked example in the prompt, or translating the question into English
   first?

## Design
| Part | Choice |
|---|---|
| Data | A fictional physiotherapy clinic: 6 patients, 3 therapists (`bench_items.py`). Two name sets share every number. No real person. |
| Items | 12 question types x 4 instances x 2 name sets = 96 items. Gold answers are computed from the records. |
| Forms | English, Roman Urdu (common spelling), Roman Urdu (chat spelling): 288 questions. |
| Methods | Direct (database in the prompt, one call); ReAct with an English example; on Roman Urdu also ReAct with a Roman Urdu example, and translate-then-ReAct. |
| Tools | `lookup_patient`, `lookup_therapist`, `calculate` (arithmetic only, no `eval`). The code runs every tool and writes the real observation. |
| Models | `qwen2.5:3b`, `llama3.2:3b`, `qwen2.5:7b`, `llama3.1:8b` through Ollama, temperature 0, seed 42. 960 calls per model. |
| Scoring | Lenient: any number in the answer matches (tolerance 0.01, or 1 point for percentages); strict: the last number must match; number words up to 20 in English and Urdu; keyword groups for therapist, specialty and days (English and Urdu day names); for "who did more", the right name must come first. |
| Diagnostics | Wrong operator (for example a minus for "saal baad"), fewer lookups than the question needs, format errors, step-limit hits, latency. |
| Statistics | Wilson 95% intervals for accuracy; paired differences on the same items with a bootstrap over items (2,000 resamples). |

| Question type | Key Roman Urdu words |
|---|---|
| T01 sessions left | baqi |
| T02 pain drop | kam hua |
| T03 age in N years | saal baad |
| T04 age N years ago | saal pehle |
| T05 combined experience | mila kar |
| T06 experience difference | zyada, kam |
| T07 total sessions of a therapist's patients (two hops) | kul |
| T08 therapist and specialty | kaun, kya |
| T09 therapist's clinic days | kin dinon |
| T10 percentage completed | kitna percent |
| T11 sessions left after two more | agar ... baqi |
| T12 which patient did more | kis ne zyada |

## Run (MacBook, Ollama open)
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                      # offline tests, no model needed
caffeinate -i python run.py              # about 5 to 6 hours for the four models
python analysis.py                       # tables and figures, no model needed
```
`run.py` can be stopped and started again; finished calls are skipped. When it finishes it commits and pushes
`results/runs.jsonl`. `python run.py --models qwen2.5:3b --limit 4 --no-push` is a two-minute check.

## Outputs
- `results/runs.jsonl`: every call with the question, answer, scores, tool calls, translation and full transcript.
- `results/tables.md`, `results/results.json`: accuracy with intervals, paired differences, error types.
- `results/fig_accuracy.png`, `results/fig_template_gap.png`.

## Results
To be filled in from the run.

## Limitations
- One fictional domain and 12 question types written by one person; real users spell Roman Urdu in more ways.
- Small open models only, run locally with default quantisation; temperature 0 gives one answer per question.
- Lenient scoring can credit an answer that mentions the right number among others; the strict score is reported
  next to it.
- The tools and system prompt are in English in every condition.
