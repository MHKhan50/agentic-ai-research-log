# A third label for the local omission judge: contradicted

**Research question:** MED-OMIT and my local omission judge ([`llm-omission-judge/`](../llm-omission-judge/)) can only say a fact is present or missing. A note that writes "left knee" for a right knee, or "no swelling" when the knee swelled, has no label of its own, and in my earlier run a judge passed such a note as present. If `qwen2.5:3b` and `llama3.1:8b` may also answer "contradicted", how many notes with a wrong side or wrong body part do they catch, how many correct notes do they wrongly call contradicted, and does the extra label make them hide more missing red flags?

This tests gap G12 in [`gap-bank.md`](../gap-bank.md).

## The paper
Schumacher, E., Rosenthal, D., Nair, V., Price, L., Tso, G. and Kannan, A. *MED-OMIT: Extrinsically-Focused Evaluation of Omissions in Medical Summarization.* arXiv:2311.08303 (2023), [arxiv.org/abs/2311.08303](https://arxiv.org/abs/2311.08303). MED-OMIT labels each fact of a consultation as present or omitted in the summary; a fact stated wrongly is outside its scale.

## Design
- **Notes (200, none drafted here):** 80 notes from [`roman-urdu-soap-benchmark/`](../roman-urdu-soap-benchmark/) (20 cases x English/Roman Urdu x 2 models) and 120 Roman Urdu notes from [`injured-side-rule/`](../injured-side-rule/) (rule, rule + glossary and retry conditions x 2 models x 20 cases). The side-rule notes are included because they hold most of the wrong sides.
- **Facts:** the case facts I wrote, plus one critical "injured area" fact per case built from the case's body region and side (for example "injured area: right ankle or foot"). C2 and C3 already list it as "side".
- **Two prompts, same judges:** `binary` is the prompt from `llm-omission-judge/` word for word (present / missing). `three` adds "contradicted" for the other side, a different body part, a different number or dose, or absent when it was present.
- **Judges:** `qwen2.5:3b` and `llama3.1:8b` through Ollama, temperature 0, seed 42, output capped at 400 tokens. One call per note with all of its facts; one retry if the reply is not usable JSON. 200 notes x 2 judges x 2 prompts = 800 calls.
- **Reference for the injured-area fact (code, English words only):** contradicted if the note names the other side, or never names the injured region but names a region the English transcript does not have; missing if the region or the expected side is absent; present otherwise. On the 200 notes this gives 69 contradicted (36 side, 33 body part), 30 missing and 101 present. All 69 contradicted notes are Roman Urdu.
- **Red flags:** for critical facts the keyword checker calls missing, I count how often each prompt calls them present ("hidden"), paired by note and fact, with an exact McNemar test.
- **Other contradictions:** there is no code reference for facts like "no swelling", so every "contradicted" call on another fact goes into a pool and 40 of them (fixed seed) go into `results/to_label.csv` for my own labels.

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q                         # 10 offline tests with a scripted fake judge
caffeinate -i python contradiction_judge.py # 800 calls; prints progress and ETA; safe to stop and restart
python analysis.py                          # no model needed; writes results/
# after filling my_label (contradicted, missing, present or unclear) in results/to_label.csv:
python analysis.py --score-labels
```

Outputs in `results/`: `runs.jsonl` (every call, with the raw reply), `area_fact.csv`, `summary.csv` (with 95% Wilson intervals), `critical.csv`, `results.json`, `to_label.csv` and `area_fact.png`.

## Results
To be filled in from my run.

## My notes
To be added after my run.

## Limitations
- 200 notes from the same 20 written consultations; one judge run at temperature 0.
- The reference for the injured-area fact reads English words only. A side or body part written only in copied Roman Urdu (for example "daayen takhne") counts as missing, which matches my earlier view that such a note is unsafe for a physiotherapist who does not read Roman Urdu, but a judge reading Roman Urdu may call it present.
- The reference is a keyword check and can be wrong; contradictions in other facts have no automatic reference and rely on my labels of 40 calls.
- All facts of a note go into one call, unlike MED-OMIT's one fact per call. The injured-area fact is added by me and is not part of MED-OMIT.
- Each judge also judges notes written by the same model, which may favour it.
