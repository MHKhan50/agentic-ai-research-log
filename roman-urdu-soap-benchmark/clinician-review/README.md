# Clinician review of the automatic checks

**Question:** Do the automatic checks in [`../checks.py`](../checks.py) agree with a physiotherapist reading the same notes? How many real errors does the safety gate miss, and how many of its flags are false alarms?

## Design
- **Notes:** all 40 Roman Urdu notes and 10 English notes (5 per model, random, seed 42), 50 in total, from [`../results/notes.jsonl`](../results/notes.jsonl).
- **Blinded:** notes are shuffled and coded R01 to R50. The sheet shows the English transcript as the reference (same facts in both languages), not the model, the input language or the automatic results. The code-to-note key is in `review_key.csv`; the reviewer does not open it.
- **Reviewer:** one registered physiotherapist. Per note she marks Y/N for: wrong or missing body region; side wrong or missing; red flag or other critical fact missing; other error. Plus a free comment.
- **Agreement (`score.py`):** for each check, a 2x2 table against her labels, raw agreement, Cohen's kappa, and precision and recall of the automatic check with her labels as the reference. The safety gate is compared with "any error" in her labels. Reported for all 50 notes and for the 40 Roman Urdu notes.

## Run
```bash
python make_sheet.py                         # review_sheet.xlsx and review_key.csv (already made)
python score.py review_sheet_filled.xlsx     # labels.csv and agreement.csv
python -m pytest -q tests                    # offline tests with a fake reviewer
```
`score.py` needs `openpyxl` for .xlsx files; a .csv exported from the Review tab also works.

## Results
Not yet available: waiting for the review.

## Limitations
- One reviewer, so no agreement between clinicians can be measured.
- The reviewer is a member of the author's family.
- "Critical fact" in the automatic check also covers medicines, referrals and urgent actions, so the reviewer's column uses the same wider definition.
