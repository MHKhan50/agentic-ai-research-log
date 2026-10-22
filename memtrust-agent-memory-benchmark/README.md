# MemTrust-Lite: a reproducible synthetic benchmark for agent-memory trust

**Research question:** In a controlled agent-memory simulator, how do provenance filtering and independent corroboration trade off memory-poisoning resistance against benign task utility?

**Why this topic:** UK research interest is evidenced by Lancaster University's currently advertised AI Agent Security PhD positions, Newcastle University's Intelligent Systems group (agentic AI, security, trustworthiness), and the University of Glasgow's 2026 agentic-AI research programme. Recent preprints also study memory poisoning and memory formation. These signals establish active research attention; they do not prove that every subtopic is “hot” or guarantee novelty.

## What this is

A small, transparent, standard-library-only Python benchmark. It creates synthetic memory records, compares three retrieval policies, writes CSV metrics, and draws SVG graphs. It is designed for teaching, dissertation prototyping, and reproducibility practice on a Mac without cloud spend or model downloads.

**Important limitation:** this is a synthetic simulator, not an evaluation of Qwen, Llama, or a deployed agent. Its output measures the simulator's assumptions, not real-world attack rates. Do not present the generated percentages as evidence about real LLM systems.

## Run on macOS (Python 3.9+)

From the extracted project folder, run this one command:

```bash
python3 run_all.py
```

Then run tests (second command):

```bash
python3 -m unittest discover -s tests -v
```

No `pip install`, network access, model download, or API key is required. The default run generates 2,250 scenarios and evaluates three policies per scenario (6,750 policy episodes) using fixed seeds.

## Policies

1. `baseline_relevance`: retrieve the highest-relevance memory regardless of provenance.
2. `provenance_filter`: require a trust score of at least 0.70.
3. `provenance_plus_corroboration`: require trust >= 0.70 and at least two corroborating sources.

Injected entries are represented only as labels and scores. The simulator does not execute malicious instructions, access files, call tools, or expose secrets.

## Output files

- `data/scenarios.csv` — scenario-level synthetic input data.
- `outputs/results.csv` — one row per scenario-policy evaluation.
- `outputs/summary.csv` — aggregate metrics by poisoning rate and policy.
- `outputs/attack_success_rate.svg` — attack success conditional on a poisoned memory being present.
- `outputs/benign_task_success.svg` — task success on clean-only scenarios.
- `outputs/overall_task_success.svg` — task success across all scenarios.
- `kaggle_upload/` — prepared CSVs, data licence, description, and references for manual Kaggle upload.

## Metrics

- **Attack success rate on poisoned episodes:** poisoned-memory selections divided by scenarios in which a poisoned memory was injected.
- **Unsafe-action rate overall:** poisoned-memory selections divided by all episodes.
- **Benign task success:** selection of the expected clean primary memory among scenarios without injected poison.
- **Overall task success:** selection of the expected clean primary memory across all scenarios.
- **Abstention rate:** no eligible memory passed a policy's filter.
- **Mean candidates considered:** number of eligible memories after filtering; a simple simulator count, not wall-clock latency or compute cost.

At poisoning rate 0%, attack success is `NA` because no poisoned episodes exist in that condition.

## Research contribution and limitations

This project offers an accessible ablation of two lightweight controls—provenance thresholding and corroboration—using transparent synthetic inputs. It is not a new state-of-the-art security method and does not establish a real-world research gap on its own. A stronger dissertation extension would validate the policy logic against a published memory-poisoning benchmark, pre-register threat assumptions, run multiple LLM backends, and report confidence intervals and benign utility costs. Preserve model/version, prompt, configuration, and dataset versions when adding LLM experiments.

## Suggested use by level

- **Undergraduate:** reproduce the simulator, test one policy threshold, explain metrics and limitations.
- **Taught Master's / MRes:** add threshold sweeps, confidence intervals, threat-model variants, and an ablation study.
- **PhD:** compare memory architectures, study memory formation and temporal provenance, then evaluate on a published benchmark with a documented agent harness.

## References and research context

See [`references/REFERENCES.md`](references/REFERENCES.md). University pages are cited as evidence of current research directions, not as endorsements of this package. No affiliation or endorsement is implied.

## Reproducibility

- Python: 3.9 or newer.
- Random seeds: 7, 13, 29.
- Tasks per seed and poisoning-rate condition: 250.
- Poisoning-rate settings: 0%, 10%, 25% (injection is sampled probabilistically, so realised rates can differ slightly).
- Dependencies: Python standard library only.
- Code licence: MIT; dataset licence: CC BY 4.0.

## Publication checklist

1. Run the script and tests on your Mac; inspect the CSVs and SVGs.
2. Keep the synthetic-only limitation prominent in any article or post.
3. Upload the individual files from `kaggle_upload/` only after reviewing them; do not claim the dataset is on Kaggle until the upload is confirmed.
4. Push the project to the research-log GitHub repository using explicit paths from the correct repository folder.
5. Publish a separate website article with the generated plots and a link to the exact repository commit.
6. If appropriate, deposit a versioned archive on Zenodo or OSF and cite the DOI only after it is minted.
7. After the website page is live, use the official [Google Search Console URL Inspection guide](https://support.google.com/webmasters/answer/9012289) to inspect the page and request indexing if available. This is a request, not a guarantee; indexing is not certification.
8. For a citable archive/DOI, consider [Zenodo](https://zenodo.org/) or [OSF](https://osf.io/) when the version is stable; do not claim a DOI until one is actually minted.

## Safety

All data are synthetic. Do not add real personal records, confidential logs, credentials, or production agent memories to this package.
