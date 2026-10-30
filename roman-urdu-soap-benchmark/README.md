# Roman Urdu vs English SOAP notes: a 20-consultation benchmark

**Research question:** Across 20 physiotherapy consultations, do two small local models (`qwen2.5:3b`, `llama3.1:8b`) leave out more facts, more critical facts and name the wrong body part or side more often when the consultation is in Roman Urdu instead of English? And how many notes would a simple safety gate send to a clinician?

This extends [`clinical-note-hallucination/`](../clinical-note-hallucination/) (4 consultations) and [`translate-then-draft/`](../translate-then-draft/). Both pilots found wrong body parts and lost red-flag answers in Roman Urdu notes, but 4 cases are too few to tell a real difference from chance.

## Setup
- **Cases:** the 4 pilot consultations plus 16 new fictional ones I wrote (`data/consultations.json`), 20 in total, each in English and Roman Urdu with the same facts and numbers. Body regions: back, neck, shoulder, knee, hip and pelvis, ankle and foot, wrist and hand, elbow. Clinical terms that clinicians in Pakistan say in English (ligament, ACL, scaphoid, carpal tunnel) are kept in English inside the Roman Urdu, as in real code-mixed speech. No real patient data.
- **Red flags on purpose:** saddle numbness and urine problems (cauda equina, C11), calf swelling after knee replacement (possible DVT, C14), weight loss with past cancer (C16), possible scaphoid fracture on warfarin (C8). A note that drops these is unsafe.
- **Facts:** 168 listed facts, 68 marked critical (red-flag answers, medicines, referrals, urgent actions).
- **Models:** `qwen2.5:3b` and `llama3.1:8b` through Ollama, temperature 0, seed 42, same note prompt as the pilots.
- **Checks (`checks.py`):** missing facts (keyword patterns), main body region present, body regions not in the transcript, injured side named, other side named without support. The **safety gate** sends a note for clinician review if any of these fail or a critical fact is missing.
- **Statistics (`summarise.py`):** facts-missing rate with a 95% bootstrap interval over cases, and an exact McNemar test on the same fact in English vs Roman Urdu for each model.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q        # offline tests (fake model)
python run.py              # 80 notes: 20 cases x 2 languages x 2 models
python summarise.py        # summary.csv, paired_tests.csv and the chart
```

## Results
From my run on a MacBook M4 (16 GB), one run at temperature 0.

| Model | Language | Facts missing | % (95% CI) | Critical missing | Wrong or missing region | Side missing / wrong | Gate flags (of 20) |
|---|---|---|---|---|---|---|---|
| qwen2.5:3b | English | _ / 168 | _ | _ | _ | _ | _ |
| qwen2.5:3b | Roman Urdu | _ / 168 | _ | _ | _ | _ | _ |
| llama3.1:8b | English | _ / 168 | _ | _ | _ | _ | _ |
| llama3.1:8b | Roman Urdu | _ / 168 | _ | _ | _ | _ | _ |

Paired test, English vs Roman Urdu (same facts): _to be filled from `results/paired_tests.csv`._

![Facts missing by language](results/facts_missing_by_language.png)

## My notes
_To be added after the run._

## Limitations
- 20 consultations I wrote, one run per model at temperature 0. Larger than the pilots but still small, and written rather than recorded speech.
- Checks are keyword based. A fact written in unexpected words counts as missing; a fact stated wrongly can count as present. "Right" can also appear as an ordinary word ("right away").
- The gate shows which notes need a person; it is not a measure of how many notes are wrong. That needs every sentence labelled.
- I wrote the Roman Urdu myself; spelling varies between speakers.

## Next steps
- Label every sentence of the flagged notes, and a sample of unflagged ones, to measure what the gate misses.
- Feed Whisper transcripts instead of clean text.
