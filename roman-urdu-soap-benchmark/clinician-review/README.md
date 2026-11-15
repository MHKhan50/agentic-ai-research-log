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
Review completed in November 2026. A panel of five physiotherapists led by Maryam Khalid (DPT; MSc Advanced Physiotherapy, Glasgow Caledonian University) labelled the 50 blinded notes together on one sheet; she then re-read every note on her own three to four times, revised labels where needed and wrote a comment per note. Labels are in `review_filled.csv`; `python score.py review_filled.csv` writes `labels.csv` and `agreement.csv`.

| Check | Both yes | Check only | Panel only | Both no | Agreement | Kappa | Precision / recall |
|---|---|---|---|---|---|---|---|
| Side wrong or missing | 27 | 0 | 3 | 20 | 0.94 | 0.88 | 1.00 / 0.90 |
| Body region wrong or missing | 16 | 3 | 3 | 28 | 0.88 | 0.75 | 0.84 / 0.84 |
| Critical fact missing | 8 | 17 | 5 | 20 | 0.56 | 0.12 | 0.32 / 0.62 |
| Gate vs any error | 38 | 1 | 4 | 7 | 0.90 | 0.68 | 0.97 / 0.90 |

The panel marked an invented or wrong detail in 35 of 40 Roman Urdu notes and 2 of 10 English notes. The side and body-region checks agree well with the clinicians; the keyword check for critical facts does not.

## Limitations
- One consensus label per item, so agreement between individual clinicians cannot be measured.
- The lead reviewer is a co-author of the paper and a member of the author's family.
- "Critical fact" in the automatic check also covers medicines, referrals and urgent actions, so the reviewer's column uses the same wider definition.
