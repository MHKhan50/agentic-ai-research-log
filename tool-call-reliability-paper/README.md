# Paper: Right Once, Wrong Next Time

> This work now has its own repository: [MHKhan50/tool-call-reliability-bench](https://github.com/MHKhan50/tool-call-reliability-bench). This folder is kept as the original snapshot.

Repeated-trial reliability (pass^k) of small local models on Roman Urdu and English clinic tool calls.

`main.tex` and `references.bib` build the paper from the results in [`../tool-call-consistency/`](../tool-call-consistency/) and [`../tool-call-self-correction/`](../tool-call-self-correction/). Every number in the paper comes from those folders.

```bash
latexmk -pdf main.tex
```

Or upload this folder as a zip to Overleaf (New Project, Upload Project).
