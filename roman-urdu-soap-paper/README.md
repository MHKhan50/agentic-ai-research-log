# Paper draft: Roman Urdu vs English SOAP notes from small local models

**Status:** working draft, not yet submitted.

`main.tex` and `refs.bib` build the paper from the results in [`../roman-urdu-soap-benchmark/`](../roman-urdu-soap-benchmark/), [`../translate-then-draft/`](../translate-then-draft/) and [`../clinical-note-hallucination/`](../clinical-note-hallucination/). Every number in the paper comes from those folders.

## Build
```bash
latexmk -pdf main.tex
```
Or upload this folder as a zip to Overleaf (New Project, Upload Project).

## Before submission
- A physiotherapist reads all 40 Roman Urdu notes and 10 English notes and marks wrong region, wrong or missing side and missing red flags, to validate the automatic checks (sheet and scoring in [`../roman-urdu-soap-benchmark/clinician-review/`](../roman-urdu-soap-benchmark/clinician-review/); waiting for the review).
- Related work has clinical note generation, code-switched benchmarks and translate-test, each reference checked against its ACL Anthology or arXiv page. Still to add: one or two Urdu or Roman Urdu LLM evaluation papers, checked the same way.
- Choose the venue and follow its format and disclosure rules.
