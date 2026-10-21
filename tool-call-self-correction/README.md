# Tool-call self-correction with a small local model

**Research question:** When a ~3B local model makes a tool call (JSON) for a clinic system, how often is it fully correct on the first try, and does feedback from a schema validator fix the errors, in English and in Roman Urdu?

## Why it matters
An agent acts through tool calls: book an appointment, record vitals, refund a payment. A common safety net is a validator that rejects malformed calls and asks the model to try again. That net can only catch what a schema can see (missing keys, wrong types, bad formats). A call that is valid JSON with the wrong time or the wrong patient passes straight through. This experiment measures both kinds of error separately.

## Setup
- **Model:** `qwen2.5:3b` through Ollama (`/api/chat`, temperature 0, seed 42). Other models can be added with `--models`.
- **Tasks:** 8 clinic tool calls (`data/tasks.json`), each asked once in English and once in Roman Urdu, so 16 calls per model. Requests include numbers in words ("seventy-two", "bahattar"), times in words ("half past two", "dopahar dhai baje"), enums and booleans.
- **Loop:** attempt 1 is the baseline. If the validator finds schema issues, the issues and the previous reply are sent back, up to 2 retries. The feedback never contains the expected values.
- **Two scores per call:**
  - *Schema valid:* what a validator can check (keys, types, `YYYY-MM-DD`, `HH:MM`, enums, ranges, bare JSON with no code fences).
  - *Fully correct:* every value matches the ground truth (case and punctuation ignored).

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q        # offline tests for the validator
python run.py              # needs Ollama running with qwen2.5:3b
python summarise.py        # writes results/summary.csv and results/self_correction.png
```

## Results
From my run on a MacBook M4 (16 GB). Counts are out of 8 tasks per language.

| Model | Language | Schema valid, first try | Schema valid, after feedback | Fully correct, first try | Fully correct, after feedback | Valid but wrong value |
|---|---|---|---|---|---|---|
| qwen2.5:3b | English | _ / 8 | _ / 8 | _ / 8 | _ / 8 | _ |
| qwen2.5:3b | Roman Urdu | _ / 8 | _ / 8 | _ / 8 | _ / 8 | _ |

![Fully correct tool calls, first try vs after validator feedback](results/self_correction.png)

## My notes
_To be added after the run._

## Earlier pilot
`results/pilot_2_tasks.json` is a first pilot with 2 English tasks (`qwen2.5:3b` and `llama3.1:8b`). All 4 calls passed on the first attempt, so the retry loop was never used, and that checker only looked at key names and types, not values. The tasks here were made harder so that the loop is actually exercised, and values are checked against the truth.

## Limitations
- 8 tasks per language is a pilot. A difference of one task is 12.5 percentage points, so small gaps mean little.
- Temperature 0 gives one deterministic answer per task; it does not show how stable the model is under sampling.
- The tasks and Roman Urdu wording were written by me; other spellings of Roman Urdu could give different results.
- The value check is an exact match after normalising case and punctuation, so a correct paraphrase of a free-text field would count as wrong.

## Next steps
- Grow to 50+ tasks with several Roman Urdu spellings, and run 5 seeds at a non-zero temperature.
- Compare with `llama3.1:8b` and with Ollama's JSON mode (`format: json`).
- Test a confirmation step ("read the call back to the user") for errors that the schema cannot catch.
