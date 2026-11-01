# Can a small local model find what a clinic note left out?

**Research question:** MED-OMIT uses GPT-4 to decide which facts from a consultation are missing from a summary. If `qwen2.5:3b` or `llama3.1:8b` does the same job on my 80 physiotherapy SOAP notes, how well does it agree with the keyword checker, is it worse on notes drafted from Roman Urdu, and does a clinically weighted omission score keep the English vs Roman Urdu gap?

## The paper
Schumacher, E., Rosenthal, D., Nair, V., Price, L., Tso, G. and Kannan, A. *MED-OMIT: Extrinsically-Focused Evaluation of Omissions in Medical Summarization.* arXiv:2311.08303 (2023), [arxiv.org/abs/2311.08303](https://arxiv.org/abs/2311.08303). Later version with D. Naik added: *MED-OMIT: Extrinsically-Focused Evaluation Metric for Omissions in Medical Summarization*, Proceedings of the 4th Machine Learning for Health Symposium, PMLR 259:897-922, 2025, [proceedings.mlr.press/v259/schumacher25a.html](https://proceedings.mlr.press/v259/schumacher25a.html).

What it does: an LLM splits a doctor-patient chat into atomic facts, checks each fact against the summary (missing = left out completely or partly), and weights each omission by how much it matters for a differential diagnosis the LLM also generates (critical 1, important 0.5, other 0.1). The score is a weighted count of omissions. The arXiv version runs the pipeline with GPT-4 on ACI-Bench (English, role-played visits) and summaries from GPT-4 and GPT-3.5-turbo; GPT-4 summaries had fewer omissions (mean count 3.72 vs 5.61). The authors note that ROUGE and BERTScore did not track the number of omissions well for the larger models.

### Gaps I see
1. **The judge is a large hosted model.** A clinic that keeps data on its own machines cannot send notes to GPT-4. Whether a 3B or 8B local model can do the omission step is not shown.
2. **English only, and importance comes from a diagnosis.** No code-mixed or Roman Urdu consultations. In physiotherapy notes the facts that matter most are often the body part, the side and red-flag answers, which a differential diagnosis does not always rank.
3. **Omission only, on a binary scale.** A fact stated wrongly (left knee written as right knee, knee written as hip) is not an omission, so the metric cannot see the errors my benchmark found most often in Roman Urdu notes.

This folder tests gap 1, on the notes from [`roman-urdu-soap-benchmark/`](../roman-urdu-soap-benchmark/).

## Setup
- **Notes:** the 80 notes in `../roman-urdu-soap-benchmark/results/notes.jsonl` (20 fictional cases x English/Roman Urdu x `qwen2.5:3b`/`llama3.1:8b`). No new notes are drafted.
- **Facts:** the 168 listed facts of those cases, 68 critical. I wrote them, so the fact-extraction step of MED-OMIT is replaced by my list.
- **Judges:** `qwen2.5:3b` and `llama3.1:8b` through Ollama, temperature 0, seed 42. One call per note with all of its facts; the reply must be JSON (`present` / `missing` per fact), with one retry if it is not.
- **Comparison:** the keyword checker from the benchmark (`checks.py`). It is not ground truth either, so every disagreement goes into `results/disagreements.csv` for me to label.
- **Weighted score:** MED-OMIT weights with my two tiers: critical fact 1, other fact 0.1.
- Each judge also judges its own notes; that may favour it.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q     # offline tests (fake model)
python judge.py         # 160 judge calls: 80 notes x 2 judges
python score.py         # agreement.csv, weighted.csv, disagreements.csv, agreement.png
```

## Results
From my run on a MacBook M4 (16 GB), one run at temperature 0.

Judge vs keyword checker (facts across 40 notes per language):

| Judge | Notes from | Parsed | Agreement % | Kappa | Missing (keywords) | Missing (judge) | Judge only | Keywords only |
|---|---|---|---|---|---|---|---|---|
| qwen2.5:3b | English | _ | _ | _ | _ | _ | _ | _ |
| qwen2.5:3b | Roman Urdu | _ | _ | _ | _ | _ | _ | _ |
| llama3.1:8b | English | _ | _ | _ | _ | _ | _ | _ |
| llama3.1:8b | Roman Urdu | _ | _ | _ | _ | _ | _ | _ |

Mean weighted omissions per note (critical 1, other 0.1):

| Note model | Language | Keywords | qwen2.5:3b judge | llama3.1:8b judge |
|---|---|---|---|---|
| qwen2.5:3b | English | _ | _ | _ |
| qwen2.5:3b | Roman Urdu | _ | _ | _ |
| llama3.1:8b | English | _ | _ | _ |
| llama3.1:8b | Roman Urdu | _ | _ | _ |

![Judge agreement](results/agreement.png)

## My notes
_To be added after the run._

## Limitations
- 80 notes from 20 consultations I wrote; one run.
- Neither the judge nor the keywords are ground truth; my labels on the disagreements are the check.
- All facts of a note go in one call, unlike MED-OMIT's one fact per call.
- No differential-diagnosis weighting; only my critical / other tiers.
- Judges see the note and the fact list, not the transcript, so they cannot catch added facts.
