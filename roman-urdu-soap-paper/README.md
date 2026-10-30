# Paper draft: Roman Urdu vs English SOAP notes from small local models

**Status:** working draft, not yet submitted.

`main.tex` and `refs.bib` build the paper from the results in [`../roman-urdu-soap-benchmark/`](../roman-urdu-soap-benchmark/), [`../translate-then-draft/`](../translate-then-draft/) and [`../clinical-note-hallucination/`](../clinical-note-hallucination/). Every number in the paper comes from those folders.

## Build
```bash
latexmk -pdf main.tex
```
Or upload this folder as a zip to Overleaf (New Project, Upload Project).

## Before submission
- A physiotherapist reads all 40 Roman Urdu notes and marks wrong region, wrong or missing side and missing red flags, to validate the automatic checks.
- Add related work on Roman Urdu and code-mixed NLP with verified references.
- Choose the venue and follow its format and disclosure rules.
