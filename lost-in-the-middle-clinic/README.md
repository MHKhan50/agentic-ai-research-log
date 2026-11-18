# Lost in the middle of a patient record

Follow-up to Liu et al., *Lost in the Middle: How Language Models Use Long Contexts*
([arXiv:2307.03172](https://arxiv.org/abs/2307.03172), published in TACL). The paper found that large
models answer best when the useful document is at the start or end of the prompt, and worst when it
is in the middle. Their tests used English Wikipedia questions and models of 7B parameters and up.

**Research question.** When one safety fact (an allergy, a pacemaker, a blood thinner) sits somewhere in
a 30-visit physiotherapy record, does a small local model (qwen2.5:3b, llama3.1:8b) find it equally well
at every position, and is it worse when the record is in Roman Urdu?

## Design
- **20 facts**, each with a question and accepted answer words (`records.py`). Examples: rash after
  diclofenac, pacemaker, warfarin, saddle numbness, 34 weeks pregnant, steroid injection.
- **Records.** 30 routine visit notes per fact. Exactly one note (the key note) holds the fact; the other
  29 are built from fixed sentence pools and are identical for every position, so only the order changes.
  The Roman Urdu record is a line-by-line translation of the English one. All notes are invented.
- **Conditions** per fact, language and model:
  - `closed_book`: the question only, to see how guessable each answer is
  - `oracle`: the key note only
  - key note at visit 1, 8, 15, 23 or 30 of 30
- **Models:** qwen2.5:3b and llama3.1:8b through Ollama, temperature 0, seed 42, context 8192 tokens,
  48 answer tokens. The prompt token count is saved for every call, so a prompt cut by the context limit
  would be visible (`possibly_cut`).
- **Scoring:** correct if an accepted answer word appears in the reply (the paper's metric).
  Tests check that the answer word appears only in the key note and never in the question.
- **Size:** 20 facts x 7 conditions x 2 languages x 2 models = 560 answers.

## Files
| File | What it does |
|---|---|
| `records.py` | facts, sentence pools, builds each record with the key note at a chosen position |
| `score.py` | answer-word matching |
| `run.py` | resumable runner, writes `results/runs.jsonl` and skips finished answers |
| `analysis.py` | accuracy per position with bootstrap 95% intervals over facts, best minus worst position, exact McNemar tests, `results/results.json`, `results/summary.csv`, `results/position_curve.png` |
| `tests/test_bench.py` | offline tests, including a full mock run with a scripted model |

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
caffeinate -i python run.py      # Ollama must be running
python analysis.py
```

## Results
Results will be added after the run on my MacBook M4.

## Limitations
- 20 facts, so one fact is 5 percentage points; intervals will be wide.
- The records are synthetic and repetitive; real notes vary more in length, wording and abbreviations.
- About 1,500 to 2,500 prompt tokens, shorter than the paper's 20 and 30 document settings.
- Keyword scoring can count a reply as correct if it lists several guesses, and can miss a correct
  paraphrase; replies are saved so they can be read.
- One run at temperature 0; one prompt wording.

## Reference
Nelson F. Liu, Kevin Lin, John Hewitt, Ashwin Paranjape, Michele Bevilacqua, Fabio Petroni, Percy Liang.
Lost in the Middle: How Language Models Use Long Contexts. arXiv:2307.03172, 2023.
https://arxiv.org/abs/2307.03172
