# Paper draft: Roman Urdu vs English for small local ReAct agents

**Status:** ready for arXiv (cs.CL) once the author has an endorsement. Every number was checked against `results.json` and `runs.jsonl`; every reference was checked against its arXiv or ACL Anthology page or is a standard statistics reference.

`main.tex` and `refs.bib` build the paper. Every number comes from [`../roman-urdu-react-bench/results/`](../roman-urdu-react-bench/results/) (tables.md, results.json and runs.jsonl), and the protocol pilot from `../roman-urdu-react-bench/results/pilot_scratchpad/`.

## Build
```bash
latexmk -pdf main.tex
```
Or upload this folder as a zip to Overleaf (New Project, Upload Project).

## Submission
- arXiv category: cs.CL (cross-list cs.AI). Licence: CC BY 4.0.
- Upload `main.tex`, `refs.bib`, `main.bbl` and `figures/`.
