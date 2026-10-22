# MemTrust-Lite: provenance and corroboration filters for agent memory

**Research question:** In a controlled agent-memory simulator, how much do a provenance (trust) filter and an independent-corroboration rule reduce poisoned-memory selection, and how much benign task success do they cost?

**Why it matters:** agents that keep long-term memory can later act on a memory that was planted by an attacker. Recent benchmarks study this with large models ([AgentPoison](https://arxiv.org/abs/2407.12784), [MemSecBench](https://arxiv.org/abs/2607.27080), [MemForm](https://arxiv.org/abs/2610.14431)). This folder is a small, fully transparent first step: it isolates the retrieval rule itself, before any LLM is involved.

**Article:** [A planted memory fooled a simple AI agent 74% of the time. A trust filter cut it to 9%.](https://masmatixinnovations.co.uk/insights/memtrust-agent-memory-security.html)

> **Scope:** this is a synthetic simulator. No LLM is called. The numbers below describe the simulator's assumptions, not real attack rates on real agents.

## Setup

Each scenario holds two clean memories and, with a set probability, one injected (poisoned) memory. Every memory has a relevance score, a trust score and a count of corroborating sources. Three retrieval policies pick one memory:

| Policy | Rule |
|---|---|
| `baseline_relevance` | highest relevance, ignore provenance |
| `provenance_filter` | trust >= 0.70, then highest relevance |
| `provenance_plus_corroboration` | trust >= 0.70 and at least 2 corroborating sources |

- 3 seeds (7, 13, 29) x 3 injection settings (0%, 10%, 25%) x 250 tasks = **2,250 scenarios**, each run under all 3 policies = **6,750 episodes**.
- Injected memories are labels only. Nothing is executed.
- Python 3.9+, standard library only.

## Results (from `outputs/summary.csv`)

| Injection | Policy | Attack success (poisoned episodes) | Benign success | Overall success |
|---|---|---|---|---|
| 10% | relevance only | 74.1% (60/81) | 100.0% | 92.0% |
| 10% | provenance filter | 8.6% (7/81) | 100.0% | 99.1% |
| 10% | provenance + corroboration | 0.0% (0/81) | 91.5% | 91.6% |
| 25% | relevance only | 70.9% (141/199) | 100.0% | 81.2% |
| 25% | provenance filter | 17.1% (34/199) | 100.0% | 95.5% |
| 25% | provenance + corroboration | 0.0% (0/199) | 92.4% | 92.8% |

At 0% injection, attack success is undefined (no poisoned episodes); benign success is 100%, 100% and 91.6%.

Charts: [`attack_success_rate.svg`](outputs/attack_success_rate.svg), [`benign_task_success.svg`](outputs/benign_task_success.svg), [`overall_task_success.svg`](outputs/overall_task_success.svg). Per-seed numbers: [`seed_summary.csv`](outputs/seed_summary.csv).

## What this does and does not show

- A trust threshold alone removed most poisoned selections at no benign cost in this simulator.
- The 0% attack success of the corroboration rule is **built in**: every injected memory is given exactly one corroborating source, so a rule that needs two can never pick it. The result restates the assumption; it is not evidence that corroboration stops real attacks.
- The price of that rule is real inside the simulator: about 8% of correct clean memories also have only one source, so benign success drops to about 92%.
- An attacker who can fake a second source, or raise trust scores, is not modelled.

## Limitations

- No LLM, no embeddings, no memory writes over time, no adaptive attacker.
- Score distributions and the 0.70 threshold are hand-chosen; results will move if they change.
- Rates are reported without confidence intervals; with 81 poisoned episodes at 10%, the provenance-filter rate is uncertain by several points.

## Next step

Let a local model (qwen2.5:3b, then llama3.1:8b) answer clinic questions with the same memories in its context, in English and Roman Urdu, and count how often it follows the injected memory. This turns the simulator into a measurement and links it to the tool-call and SOAP-note experiments in this log (gap G8 in [gap-bank.md](../gap-bank.md)).

## Run

```bash
python3 run_all.py                         # writes data/ and outputs/
python3 -m unittest discover -s tests -v   # 5 tests
```

## Files

| Path | Content |
|---|---|
| `src/memtrust.py` | scenario generator, policies, metrics, SVG charts |
| `data/scenarios.csv` | 2,250 synthetic scenarios |
| `outputs/results.csv` | one row per scenario and policy (6,750) |
| `outputs/summary.csv`, `outputs/seed_summary.csv` | aggregated metrics |
| `docs/data_dictionary.md` | column definitions |
| `notebooks/starter.ipynb` | quick look at the CSVs (also used on Kaggle) |

## Licence

Code: MIT (see the repository [LICENSE](../LICENSE)). Synthetic data: CC BY 4.0 (see [DATA_LICENSE.md](DATA_LICENSE.md)).

## References

See [references/REFERENCES.md](references/REFERENCES.md).
