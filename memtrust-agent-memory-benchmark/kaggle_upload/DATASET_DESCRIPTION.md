# MemTrust-Lite: Synthetic Agent Memory Poisoning Benchmark

## Short description

Synthetic benchmark data for studying how provenance filtering and independent corroboration affect agent-memory poisoning resistance and benign task utility. Includes generated scenarios, policy-level outcomes, aggregate metrics, and references.

## About this dataset

All records are generated locally by the accompanying Python script. No real users, production agent logs, confidential information, or external dataset rows are included. The benchmark is a transparent simulator, not an evaluation of real LLMs. Reported rates describe the simulator assumptions only and must not be generalized to deployed agents.

## Files

- `scenarios.csv`: synthetic memory candidates, relevance/trust/corroboration scores, poison-presence label, seed, and scenario ID.
- `results.csv`: policy-level selections and outcomes for each scenario.
- `summary.csv`: aggregate attack-success, benign utility, overall utility, abstention, and candidate-count metrics by policy and injection rate.
- `DATA_LICENSE.md`: dataset licence and attribution.
- `REFERENCES.md`: literature and current UK research-context links.

## Intended uses

Teaching, dissertation prototyping, reproducibility exercises, and policy ablations. Not suitable for estimating real-world attack rates or certifying agent safety.

## Licence

CC BY 4.0 for dataset files. See `DATA_LICENSE.md`. Upload the individual CSV and documentation files after reviewing them; this archive does not mean the dataset is already published on Kaggle.
