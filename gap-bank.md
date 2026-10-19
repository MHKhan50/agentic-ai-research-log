# Gap bank

Running list of research gaps found while reading papers. Status: `open` → `testing` → `results` → `write-up`.

| # | Paper | Gap | Feasible on M4 16 GB in ~1 week? | Status | Folder |
|---|---|---|---|---|---|
| G1 | Yao et al. 2022, *ReAct* ([arXiv:2210.03629](https://arxiv.org/abs/2210.03629)) | All benchmarks English; prompted results only from very large models (PaLM-540B, GPT-3). Untested: small local models on Roman Urdu / code-mixed questions. | Yes, 3B model via Ollama, 24 questions | results (pilot, 2 runs): ReAct Roman Urdu 83% → 58% after a name swap (English 92% → 83%); unstable at n=12. Next: 50+ questions, several name sets | `react-roman-urdu/` |
| G2 | Yao et al. 2022, *ReAct* | No high-stakes / clinical setting and no abstention: the agent always answers, even after uninformative lookups (authors report 23% of ReAct errors from uninformative search). | Partly, needs a "not found → say I don't know" test set | open | - |
| G3 | Yao et al. 2022, *ReAct* | Authors note loops of repeated thoughts/actions (possibly greedy decoding); not measured for small models. | Yes, count repeated actions in `trajectories.jsonl` | open | - |
| G4 | Yao et al. 2022, *ReAct* | The paper's error analysis found no hallucination in ReAct's sampled failures (large models, English). With a 3B model, ReAct still invented a fact after skipping a lookup (Roman Urdu Q03). | Yes, count unsupported facts in final answers across runs | open | `react-roman-urdu/` |
| G5 | Radford et al. 2022, *Whisper* ([arXiv:2212.04356](https://arxiv.org/abs/2212.04356)) | Multilingual results are on read-speech benchmarks (FLEURS, MLS, VoxPopuli); no clinical conversation and no Urdu-English code-switching. Authors list skipped words and hallucinated text as failure modes, but WER does not show whether clinically important words survive. | Yes, faster-whisper tiny/base/small on CPU, self-recorded fictional clips | testing | `whisper-urdu-wer/` |
