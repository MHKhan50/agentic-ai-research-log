# Whisper on Urdu clinic speech: word error rate and clinical terms

**Research question:** On short Urdu doctor-patient conversations with everyday English medical words mixed in, how many words does Whisper (tiny, base, small) get wrong on a MacBook, and does it keep the clinically important words?

## Why it matters
Clinical documentation tools (live transcription, then an LLM drafts the note) are only as safe as the transcript. In Pakistan and in UK clinics with Urdu-speaking patients, consultations are spoken in Urdu mixed with English terms such as *X-ray*, *MRI*, *sugar* and *blood pressure*. Whisper ([Radford et al., 2022](https://arxiv.org/abs/2212.04356)) reports multilingual results on read-speech benchmarks such as FLEURS. It does not evaluate clinical conversation or code-switching, and the authors list skipped words and hallucinated text as known failure modes. A single missed word like *peshab* (urine) or *bukhar* (fever) can hide a red flag, so word error rate alone is not enough.

## Data
- Three fictional physiotherapy conversations written in Urdu script: lower back pain with red-flag questions, a twisted knee, and a frozen shoulder ([`data/references/`](data/references/)). About 200 words in total.
- Read aloud by me in my own voice and recorded at 16 kHz mono on the MacBook microphone. **No real patient data.** The audio stays on my machine and is not committed.
- [`data/key_terms.json`](data/key_terms.json): 24 clinical key terms (8 per clip) with accepted spellings in Urdu and Latin script, e.g. `ایم آر آئی` or `MRI`.

## Method
1. **Transcription:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2), CPU, int8, `language="ur"`, beam size 5, temperature 0. Models: tiny, base, small.
2. **Normalisation** ([`urdu_text.py`](urdu_text.py)): Arabic yeh/kaf/heh mapped to Urdu forms, diacritics and punctuation removed, digits unified. The same function runs on the reference and the transcript, so keyboard differences are not counted as errors.
3. **Metrics** ([`metrics.py`](metrics.py)):
   - **WER** = (substitutions + deletions + insertions) / reference words, from a Levenshtein alignment.
   - **CER** on characters with spaces removed, because Urdu word spacing is inconsistent (`فزیوتھراپی` vs `فزیو تھراپی`).
   - **Key-term recall:** share of the 24 clinical terms that appear in the transcript.
   - **Real-time factor:** transcription time / audio length (below 1 means faster than real time).
   - **Language ID:** whether Whisper, left to guess, detects the clip as Urdu.
4. Results are pooled over clips (total errors / total reference words).

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python run_wer.py                 # records missing clips, then writes results/
python run_wer.py --models medium # optional, larger model
```
If `data/audio/clip1.wav` (or `.m4a`) is missing, the script opens a reading sheet and records it: Enter to start, Enter to stop. Whisper models download on first use (tiny ~75 MB, base ~145 MB, small ~480 MB).

## Results
From my run on a MacBook M4 (16 GB), 3 clips, 203 reference words, 24 key terms.

| Model | WER | CER (no spaces) | Key terms recovered | Real-time factor | Auto-detected as Urdu |
|---|---|---|---|---|---|
| tiny | 43.8% | 19.9% | 50% | 0.04 | 33% |
| base | 29.1% | 11.2% | 46% | 0.05 | 0% |
| small | 19.2% | 7.7% | 54% | 0.13 | 0% |

![WER by model](results/wer_by_model.png)

**Main finding:** a bigger model more than halved the word error rate (43.8% to 19.2%), but clinical key-term recall stayed flat at about 50% (46% to 54%). Model size helped everyday Urdu, not the clinical words.

What the transcripts show (small model, from [`results/word_errors.csv`](results/word_errors.csv)):
- **Most errors are spelling, not hearing.** CER is far below WER (7.7% vs 19.2%), so most wrong words are one or two letters off. The aspirated *do-chashmi he* (ھ) is often dropped: گھٹنا → گٹنا, کندھے → کندے, چڑھتے → چڑتے (6 of 33 substitutions are only a missing ھ). Retroflex letters are also confused: ڈاکٹر → دکٹر, سیڑھیاں → سیڈیاں, ٹانگ → طانگ.
- **English medical words are the weakest.** No model wrote X-ray or MRI correctly (MRI became مرائی or امرائی). Physiotherapy became فیزیو تیاریپی.
- **"Pain" turned into a Persian word.** In clips 2 and 3 the small model wrote درد (pain) as دارد three times. "Pain" was only on the key-term list for clip 1, so the key-term score did not catch this: a fixed term list misses errors on words it does not include.
- **Language ID:** left to guess, base and small labelled every clip as Hindi. Forcing `language="ur"` is required, or the output may come out in Devanagari.
- **Speed:** small transcribed 36 seconds of audio in about 4.7 seconds, roughly 8 times faster than real time, on CPU.

Per-clip numbers: [`results/results.csv`](results/results.csv). Raw transcripts: [`results/transcripts/`](results/transcripts/).

## My observations
- Moving from tiny to small cut WER by more than half, yet clinical key terms stayed around 50%. Clinical words and English terms spoken inside Urdu are rare in general training data, so the model often hears the sound but writes an unfamiliar spelling.
- For MeetPhysio I would choose **small**. Base recovered fewer key terms than tiny (46% vs 50%), while small was best on every measure and, at a real-time factor of 0.13, is still fast enough for live use. Even small missed every X-ray and MRI, so model choice alone will not fix English medical terms.
- I listened back to clip 3 and confirmed that I said "مشکل" where the script had "تکلیف". The model was right there, so part of the measured error comes from my reading, not from Whisper.

## Limitations
- One speaker, three clips, read speech in a quiet room. Real consultations have two voices, interruptions, background noise and regional accents. These numbers are a smoke test, not a benchmark.
- The reference scripts were written before recording. Confirmed reading deviation: "مشکل" for "تکلیف" in clip 3 (counted as an error for every model). A few other differences ("لیتے" for "لیتی", an extra "بھی") appear in both base and small and may also be my reading; they were not checked.
- Digits vs words are not unified: small wrote "6" where the reference has "چھ", which counts as an error.
- Key-term recall checks whether a term appears at least once in the clip, using listed spellings only. A correct but unlisted spelling counts as a miss, and a term that is right once but wrong elsewhere counts as found.
- Urdu vs Hindi script: if Whisper writes Devanagari, every word counts as wrong even when the sound was right. Here the language was forced to Urdu, so this did not happen.

## Next steps
- **Fix the clinical words cheaply first:** pass a short medical vocabulary as Whisper's `initial_prompt` and measure whether key-term recall rises, without retraining.
- Score terms per occurrence (not just presence) and add a sound-alike match (e.g. ignoring a missing ھ) to separate "heard but misspelled" from "not heard".
- Add a second speaker and background noise (clinic fan, traffic); compare with `medium` and an Urdu fine-tuned Whisper.
- Feed the transcripts into the local LLM note-drafting step and check whether transcript errors change the red-flag section of the note.
