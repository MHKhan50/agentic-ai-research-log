# Translate first, or draft directly? Roman Urdu SOAP notes from small local models

**Research question:** For Roman Urdu physiotherapy consultations, does translating the transcript into English first and then drafting the SOAP note keep more key facts and the right body part than drafting directly, and does a larger local model (`llama3.1:8b`) change the answer?

This follows [`clinical-note-hallucination/`](../clinical-note-hallucination/), where `qwen2.5:3b` left out 13 of 42 listed facts in Roman Urdu notes (2 of 42 in English) and wrote about the wrong body part in 3 of 4 Roman Urdu notes. There I suggested translate-then-draft as a fix, with the risk that the translation step makes the same mistakes. This experiment measures it.

## Setup
- **Models:** `qwen2.5:3b` and `llama3.1:8b` through Ollama (temperature 0, seed 42).
- **Data:** the same 4 fictional consultations and fact lists as `clinical-note-hallucination/data/consultations.json` (reused, not copied). No real patient data.
- **Conditions** per model and consultation:
  - `en-direct`: English transcript to note (reference)
  - `ru-direct`: Roman Urdu transcript to note
  - `ru-translate`: the same model translates the Roman Urdu transcript into English, then drafts the note from its own translation
- **Note prompt:** identical to the earlier experiment, so the numbers are comparable.
- **Omissions:** the same keyword patterns per listed fact. For `ru-translate`, the patterns are also run on the translation, to see whether a fact was lost in translation or in drafting.
- **Body region check (new, `body_checks.py`):** a note must name the consultation's main region (back, knee, shoulder, neck) and should not name a region that never appears in the English transcript. Run on the 8 earlier `qwen2.5:3b` notes, it flags exactly the 3 Roman Urdu notes with a wrong body part (C1 knee, C2 groin, C4) and none of the English notes.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q        # offline tests (no model needed)
python run.py              # 24 notes + 8 translations, both models
python summarise.py        # results/summary.csv and the chart
```

## Results
_To be filled from my run._

| Model | Condition | Facts missing (of 42) | Critical missing | Main region missing (of 4) | Notes naming other regions | Mean seconds |
|---|---|---|---|---|---|---|
| qwen2.5:3b | en-direct | | | | | |
| qwen2.5:3b | ru-direct | | | | | |
| qwen2.5:3b | ru-translate | | | | | |
| llama3.1:8b | en-direct | | | | | |
| llama3.1:8b | ru-direct | | | | | |
| llama3.1:8b | ru-translate | | | | | |

Files: `results/notes.jsonl` (notes and translations), `results/omissions.csv`, `results/body_regions.csv`, `results/summary.csv`, `results/translate_vs_direct.png`.

## My notes
_To be added after reading the notes and translations._

## Limitations
- 4 consultations, one run per condition at temperature 0. A pilot, not a benchmark.
- Omission and body-region checks are keyword based. A fact written in unexpected words counts as missing; a fact stated wrongly can still count as present. The body-region check catches a wrong region only if that region's word appears in the note.
- The fact patterns were written for notes, so "missing in translation" can over-count (for example a translation that says "about 6" without "out of 10").
- Sentence-level hallucination labels are not repeated here; this run measures omissions and body-region errors only.
- Transcripts are clean text, not speech-to-text output.
