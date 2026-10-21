# ToolGuard: validation gates and bounded retries for tool-using agents

**Research question:** In a fixed ticket-triage workflow, how do a pre-execution validation gate and bounded retries change task completion, invalid tool actions and tool-call cost as tool failures become more frequent?

## Why it matters
An agent can fail in two different ways: it can propose an invalid action (wrong argument, closing a ticket too early), or a valid tool call can fail at runtime. A validation gate targets the first problem and retries target the second. This project separates the two so their effect and their cost can be measured on their own and together. It follows on from [`tool-call-self-correction/`](../tool-call-self-correction/), where a schema validator never fired because the model's errors were in the values, not the format.

## Setup
- **Workflow:** synthetic ticket triage. Inspect a ticket, set priority from severity, assign the team from category, add a note, and close only when everything is set. 120 generated tickets (`data/tasks.csv`), no real data.
- **Policies:** `baseline` (no gate, no retry), `retry_only`, `guard_only` (validates and repairs arguments, blocks early closure) and `guard_retry` (both).
- **Conditions:** 12% plan noise; tool-failure rates of 0%, 10% and 25%; a budget of 8 tool calls; up to 2 retries after the first attempt; seed 7. 1,440 episodes in total.
- **Two experiments, reported separately:**
  1. **Simulator:** a scripted planner injects known errors, so the effect of the gate and the retries can be isolated. This does not measure LLM reasoning.
  2. **Local LLM pilot:** `qwen2.5:3b` through Ollama chooses the actions itself, on 8 tickets at a 10% failure rate.

## Run
Python 3.9+, standard library only:
```bash
python3 -m unittest discover -s tests -v
python3 run_experiment.py --tasks 120 --seed 7
python3 plot_results.py
python3 run_ollama.py --model qwen2.5:3b --tasks 8 --seed 7 --tool-failure-rate 0.10   # optional, needs Ollama
```

## Results

### 1. Simulator (120 tickets per condition)
| Tool-failure rate | Policy | Task success | Invalid-action rate | Mean tool calls |
|---:|---|---:|---:|---:|
| 0% | Baseline | 50.8% | 8.0% | 5.00 |
| 0% | Retry only | 50.8% | 8.0% | 5.00 |
| 0% | Guard only | 100.0% | 0.0% | 5.00 |
| 0% | Guard + retry | 100.0% | 0.0% | 5.00 |
| 10% | Baseline | 30.0% | 16.3% | 5.00 |
| 10% | Retry only | 49.2% | 7.2% | 5.54 |
| 10% | Guard only | 61.7% | 0.0% | 4.37 |
| 10% | Guard + retry | 97.5% | 0.0% | 5.53 |
| 25% | Baseline | 13.3% | 20.7% | 5.00 |
| 25% | Retry only | 44.2% | 7.0% | 6.40 |
| 25% | Guard only | 24.2% | 0.0% | 3.79 |
| 25% | Guard + retry | 85.0% | 0.0% | 6.30 |

Full table: [`outputs/summary.csv`](outputs/summary.csv). Figures: [`outputs/figures/`](outputs/figures/).

- The gate removed invalid actions, but on its own it fell to 24% success at a 25% failure rate, because failed calls were not retried.
- Retries on their own helped with failures but could not fix bad arguments.
- Together they had the highest success in every condition, at the cost of more tool calls; at 25% failure, 10.8% of guard + retry episodes still ran out of budget.
- The gate's 0% invalid-action rate follows from the simulator's design: the gate knows the correct category and severity mappings. It is not evidence that a real validator would catch everything.

### 2. Local LLM pilot (qwen2.5:3b, 8 tickets, 10% failure rate)
| Policy | Task success | Invalid-action rate | Mean tool calls |
|---|---:|---:|---:|
| Unguarded | 62.5% (5/8) | 9.4% | 6.63 |
| Guard + retry | 100.0% (8/8) | 0.0% | 5.13 |

Files: [`outputs/ollama/`](outputs/ollama/). Eight tickets is a pilot: one ticket is 12.5 percentage points.

## Limitations
- The simulator encodes the rules that the gate checks, so the simulator results show how the mechanisms interact, not how well they work on real agents.
- One seed and no confidence intervals.
- The LLM pilot has 8 tickets, one model and one run.
- One synthetic workflow; real tools have more varied failures.

## Next steps
- Repeat over several seeds and report intervals.
- Run the LLM pilot on all 120 tickets and with `llama3.1:8b`.
- Compare a gate that blocks with one that repairs, and use the clinic tool calls from [`tool-call-self-correction/`](../tool-call-self-correction/) as a second, more realistic workflow.

## Licence
Code: MIT ([`LICENSE`](LICENSE)). Generated data: CC0 1.0 ([`DATA_LICENSE.txt`](DATA_LICENSE.txt)).
