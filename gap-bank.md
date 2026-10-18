# Gap bank

Running list of research gaps found while reading papers. Status: `open` → `testing` → `results` → `write-up`.

| # | Paper | Gap | Feasible on M4 16 GB in ~1 week? | Status | Folder |
|---|---|---|---|---|---|
| G1 | Yao et al. 2022, *ReAct* ([arXiv:2210.03629](https://arxiv.org/abs/2210.03629)) | All benchmarks English; prompted results only from very large models (PaLM-540B, GPT-3). Untested: small local models on Roman Urdu / code-mixed questions. | Yes, 3B model via Ollama, 24 questions | results (pilot): qwen2.5:3b ReAct 92% EN / 83% RU vs direct 75% / 50% (n=12). Next: more questions, more models | `react-roman-urdu/` |
| G2 | Yao et al. 2022, *ReAct* | No high-stakes / clinical setting and no abstention: the agent always answers, even after uninformative lookups (authors report 23% of ReAct errors from uninformative search). | Partly, needs a "not found → say I don't know" test set | open | - |
| G3 | Yao et al. 2022, *ReAct* | Authors note loops of repeated thoughts/actions (possibly greedy decoding); not measured for small models. | Yes, count repeated actions in `trajectories.jsonl` | open | - |
