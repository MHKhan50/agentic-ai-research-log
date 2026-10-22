# Data dictionary

## `data/scenarios.csv`

- `scenario_id`: deterministic identifier for one synthetic scenario.
- `seed`, `task_index`: random seed and within-condition task number.
- `poisoning_rate`: nominal probability of adding a poisoned candidate (0, 0.10, or 0.25); realised sample proportions can differ.
- `poison_present`: whether the synthetic poisoned candidate was included (0/1).
- `primary_clean_relevance`, `primary_clean_trust`, `primary_clean_corroboration`: features for the expected clean memory.
- `secondary_clean_relevance`, `secondary_clean_trust`, `secondary_clean_corroboration`: features for a lower-relevance clean distractor.
- `poison_relevance`, `poison_trust`, `poison_corroboration`: features for the injected candidate; blank when no poisoned candidate exists.
- `expected_memory_id`: always `clean_primary` in this benchmark.
- `poisoned_memory_id`: label of the injected candidate or blank.
- `scenario_note`: explicit synthetic-data disclaimer.

## `outputs/results.csv`

One row per scenario-policy pair. `selected_memory_id` is the selected label or `ABSTAIN`; `selected_memory_is_poisoned` and `attack_success` are 0/1 indicators; `task_success` is 1 only when the expected `clean_primary` memory is selected; `abstained` indicates that no candidate passed the policy; `candidates_considered` is the number of eligible candidates after filtering.

## `outputs/summary.csv` and `outputs/seed_summary.csv`

Aggregate metrics by poisoning rate and policy; `seed_summary.csv` additionally preserves each random seed separately. Rates are proportions from 0 to 1, not percentages. `NA` means the denominator is zero.
