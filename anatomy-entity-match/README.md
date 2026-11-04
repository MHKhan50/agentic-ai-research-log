# Soft anatomy matching vs wrong sides and body parts

**Paper:** Zhao, Wu, Zhang, Zhang, Wang and Xie, *RaTEScore: A Metric for Radiology Report Generation*, 2024 ([arXiv:2406.16845](https://arxiv.org/abs/2406.16845)).

RaTEScore pulls medical entities out of a generated report and its reference (anatomy, abnormality, disease and their negated forms), embeds each entity with BioLORD-2023-C, matches every entity to its most similar entity on the other side, and takes the harmonic mean of the two directions. It agreed with radiologists better than BLEU, ROUGE-L, BERTScore and RadGraph F1 on its own RaTE-Eval set and on ReXVal. The paper does not discuss left and right, and its data is English radiology reports.

**Research question:** In my Roman Urdu SOAP benchmark the most common errors were a wrong or missing injured side and a wrong body part. Does RaTEScore-style soft matching of anatomy notice these errors, or does it score "left knee" almost the same as "right knee"? And how does it compare with a plain code check?

This is **not** RaTEScore itself: there is no NER model and no learned type weights. Anatomy phrases ("right ankle", "lower back") are read with the word lists from [`side-mismatch-check/`](../side-mismatch-check/) and scored with the same encoder the paper uses (BioLORD-2023-C, Eqs. 1-3 without weights). No LLM is called.

## What runs
| Part | Input | Question |
|---|---|---|
| Probe | 10 fixed phrase pairs | How similar does the encoder find a side swap, a body-part swap, a synonym? |
| Notes | the same 200 notes as [`side-mismatch-check/`](../side-mismatch-check/) (40 English, 160 Roman Urdu) | Does the soft score separate unsafe notes from safe ones? |
| Swaps | every safe English note with left and right swapped, and with its main body part swapped (knee to ankle, shoulder to elbow, back to neck) | Does the score drop when only the side or the part changes? |

**Reference label:** a note is unsafe if the side is missing, wrong or not in the transcript (as in `side-mismatch-check/`), the main body region is missing, or it names a region the English transcript never mentions.

**Soft score flag:** a note is flagged when its score is below the cut that flags about 5% of safe notes. **Code check:** flags a note when its side words or body regions disagree with the spoken transcript (no encoder).

## Run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q          # 7 offline tests (letter-count stand-in encoder)
python entity_match.py       # first run downloads BioLORD-2023-C (about 0.4 GB), then about a minute
```

## Results
_To be filled from my run._

| | Value |
|---|---|
| Encoder similarity, side swap (right knee vs left knee) | _ |
| Encoder similarity, part swap (right ankle vs right knee) | _ |
| Encoder similarity, synonym (lower back vs lumbar spine) | _ |
| AUROC of soft score, unsafe vs safe notes | _ |

| Set | Notes | Soft score flagged | Code check flagged |
|---|---|---|---|
| Real unsafe notes | _ | _ | _ |
| Side swaps | _ | _ | _ |
| Part swaps | _ | _ | _ |
| Safe notes (false flags) | _ | _ | _ |

![Soft score vs code check](results/soft_vs_code.png)

## My notes
_To be added after the run._

## Limitations
- RaTEScore-style, not RaTEScore: no entity extractor model, no learned weights, anatomy entities only. A full RaTEScore run could rank notes differently.
- The phrases come from word lists, so a body part written in an unusual way is missed by both the soft score and the code check.
- The reference label uses the same word lists as the code check, so the code check has a built-in advantage on the real notes; the swap test does not have this problem, because the error is known by construction.
- 20 fictional consultations, one run of notes per condition, one author labelling.
