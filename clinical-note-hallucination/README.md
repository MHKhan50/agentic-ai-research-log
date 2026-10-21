# Hallucinations and omissions in SOAP notes from a small local model

**Research question:** When a ~3B local model drafts physiotherapy SOAP notes from consultation transcripts, how many key facts does it leave out and how many sentences does it add without support, and is this worse when the consultation is in Roman Urdu?

## Paper this follows
Asgari E., Montaña-Brown N., Dubois M., Khalil S., Balloch J., Au Yeung J., Pimenta D. (2025). *A framework to assess clinical safety and hallucination rates of LLMs for medical text summarisation.* npj Digital Medicine 8, 274. [doi:10.1038/s41746-025-01670-7](https://doi.org/10.1038/s41746-025-01670-7) ([preprint](https://www.medrxiv.org/content/10.1101/2024.09.12.24313556))

They had clinicians label 12,999 sentences of GPT-4 notes written from 450 simulated UK primary-care consultations (English). They found a 1.47% hallucination rate and a 3.45% omission rate; 44% of hallucinations were major, most often in the Plan. Their limitations: one model (GPT-4), English only, and expensive manual labelling. This experiment asks the same question for a small model that runs on a laptop, in English and Roman Urdu.

## Setup
- **Model:** `qwen2.5:3b` through Ollama (temperature 0, seed 42). Another model can be passed with `--model`.
- **Data:** 4 short fictional physiotherapy consultations I wrote (`data/consultations.json`): low back pain, twisted knee, stiff shoulder with diabetes, neck pain from desk work. Each one exists in English and in Roman Urdu with the same facts and digits, so 8 notes in total. No real patient data.
- **Prompt:** write a concise English SOAP note (Subjective, Objective, Assessment, Plan) using only information in the transcript.
- **Omissions (automatic):** each consultation has 10-11 listed facts, some marked *critical* (red-flag answers, medication, side, referrals). A fact counts as missing if its keyword pattern is absent from the note.
- **Hallucinations (my labels):** the checker flags note sentences with a number or drug name not in the transcript, or a denied symptom stated without a negation. Every Plan sentence is also reviewed, because the paper found most major hallucinations there. I label each reviewed sentence with `label.py` as `ok` or `H` (unsupported), and each `H` as `major` (could change diagnosis or management) or `minor`, following the paper's definition.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q        # offline tests for the checker
python run.py              # drafts 8 notes, writes results/review.csv
python label.py            # label each reviewed sentence in the terminal (o/h, then m/n)
python summarise.py        # writes results/summary.csv and the chart
```

## Results
From my run on a MacBook M4 (16 GB), `qwen2.5:3b`, one run at temperature 0. 4 notes per language, 42 listed facts per language.

| Language | Listed facts missing | Critical facts missing | Sentences reviewed | Unsupported (my labels) | Major |
|---|---|---|---|---|---|
| English | 2 / 42 | 0 | 14 | 3 | 1 |
| Roman Urdu | 13 / 42 | 7 | 12 | 4 | 2 |

![Omissions and hallucinations by language](results/omissions_hallucinations.png)

**Main finding:** from the same consultations, the Roman Urdu notes left out 13 of 42 listed facts against 2 of 42 in English, including 7 critical ones (the red-flag answers about numbness, urine, tingling and dizziness, the injured side, and the knee giving way). The English notes kept every critical fact.

**Reading the full notes shows more than the labels capture.** In 3 of the 4 Roman Urdu notes the body part is wrong (from [`results/notes.jsonl`](results/notes.jsonl)):
- **C1:** lower back pain ("kamar ke nichle hisse") became "pain in the **knees**", with exercises "for the knees". The same note says both "does not take any medications" and "takes Ibuprofen 400 mg".
- **C2:** a swollen right knee ("daayan ghutna") became a "**groin strain**" with "**no swelling**".
- **C4:** neck pain ("gardan") became "**shoulder** pain"; "chakkar nahi" (no dizziness) became "no circular motion", and the note added "a 45-year-old male" with "no known allergies", none of which was said.
- **C3:** "10 mein se 5" (pain 5 out of 10) became night pain "starting around 10 PM and lasting up to 5 hours".

The English notes were close to the transcripts. The one major error there was in the Plan: "crutches if needed" became "use crutches to avoid putting weight on the injured knee".

**What the checker missed.** Only flagged and Plan sentences were reviewed (26 of 129). Most Roman Urdu errors sat in Subjective, Objective and Assessment, so the labelled count (4) understates them. The invented "10 PM / 5 hours" passed the number check because 10 and 5 appear in the transcript. Of 26 reviewed sentences, the checker flagged only 1; the other confirmed errors were found by reviewing Plan sentences.

Files: [`results/summary.csv`](results/summary.csv), [`results/omissions.csv`](results/omissions.csv), [`results/review.csv`](results/review.csv) (my labels).

## My notes
- The most dangerous result was the wrong body part in the Roman Urdu notes: lower back became knees, knee became groin, and neck became shoulder. In a live clinic this would lead to the wrong examination and the wrong physiotherapy treatment.
- The checker missed "10 PM / 5 hours" because it only checks whether numbers and words appear in the transcript, not what they mean. A better check would read the whole note, including Subjective and Assessment, for example an LLM-as-a-judge with clinician review, as the paper suggests. A judge model can also hallucinate, so it would need its own test.
- For a small local model, reading Roman Urdu directly was unreliable here. One option for MeetPhysio is to translate the Roman Urdu transcript into English first and then draft the note. This is a hypothesis: the translation step could make the same mistakes ("chakkar" as "circular motion"), so it needs its own measurement.

## Limitations
- 8 notes from 4 consultations I wrote and one model at temperature 0. A pilot, not a benchmark.
- Omission checks are keyword based: a fact written with unexpected words counts as missing, and a fact stated wrongly (for example a denied symptom written as present) still counts as present. The negation flag is there to catch the second case.
- Only flagged and Plan sentences were labelled (26 of 129). This missed most Roman Urdu errors, which were in Subjective, Objective and Assessment; the body-part errors above come from reading the full notes, not from the labels.
- I labelled the sentences myself; the paper used two clinicians per note and a senior reviewer.
- Transcripts are clean text. Real notes would start from speech-to-text, which adds its own errors (see [`whisper-urdu-wer/`](../whisper-urdu-wer/)).

## Next steps
- Label every sentence of all 8 notes to get a complete hallucination count.
- Test translate-then-draft against direct drafting on the same Roman Urdu consultations.
- Compare `llama3.1:8b`, and test the paper's best prompt ideas (a template and a revision step) on the same notes.
- Feed Whisper transcripts instead of clean text and measure how transcript errors change the note.
