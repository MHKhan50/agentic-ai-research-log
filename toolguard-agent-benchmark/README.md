# ToolGuard: Budgeted Reliability for Tool-Using Agents

**Version:** 0.1.0
**Date prepared:** 21 October 2026
**Audience:** UK undergraduate dissertation students, taught/research master's and MRes students, and PhD researchers.

## What this project asks

**Research question:** Under a fixed synthetic workflow, how do pre-execution validation, prerequisite gating, and bounded retries affect task completion, invalid tool actions, and tool-call overhead as transient tool failures increase?

The package compares four controlled policies:

1. `baseline` — no validation gate and no retry.
2. `retry_only` — retries transient tool failures, but does not repair bad arguments or block unsafe closure.
3. `guard_only` — validates/repairs arguments and gates closure, but does not retry transient failures.
4. `guard_retry` — combines the gate with bounded retries.

The task is a **synthetic ticket-triage workflow**: inspect a ticket, set priority from severity, assign the team from category, add a note, and close only after prerequisites are satisfied. Tool failures and plan noise are independently controlled. The default benchmark uses 120 generated tickets, a fixed noise rate of 12%, tool-failure rates of 0%, 10%, and 25%, a maximum of 8 tool calls per episode, and up to 2 retries after the initial attempt.

### Important scope limitation

The default experiment is a **controlled simulator**, not a measurement of LLM reasoning, real customer support, or production reliability. Its scripted planner deliberately introduces known errors so the effects of guardrails and retries can be isolated. The optional `run_ollama.py` script adds a local-model experiment using Ollama, but model runs are slower and may vary across model builds. Report the simulator and Ollama results separately.

The project is motivated by the kinds of questions currently visible in UK institutional research: Ulster University lists trust-aware agents, explainability, adaptive decision-making, and safe operation in dynamic environments; Glasgow Computing Science identifies AI, autonomous systems, HCI, and research degrees including MRes; UCL's foundational-AI studentship includes sequential decision-making and computational experiments. These sources demonstrate institutional interest, **not proof that the specific research question is novel**. Conduct a literature review before claiming a research gap.

## Fast start on macOS (Python 3.9.6 compatible; no pip install required)

Open Terminal, change directory into the unzipped `toolguard_agent_benchmark` folder, then run:

```bash
python3 -m unittest discover -s tests -v && python3 run_experiment.py --tasks 120 --seed 7 && python3 plot_results.py
```

This is one copy-paste command block. It runs the tests, runs the benchmark, and generates three SVG figures in `outputs/figures/`. The core project uses only the Python standard library. If `python3` points to a different Python installation, check with `python3 --version` first.

### Output files

- `data/tasks.csv` — 120 synthetic tickets, no real personal data.
- `outputs/results.csv` — one row per task, policy, and failure-rate condition.
- `outputs/summary.csv` — aggregate metrics by policy and failure rate.
- `outputs/run_metadata.json` — seed, parameters, Python version, and scope note.
- `outputs/figures/success_rate.svg` — task completion by failure rate.
- `outputs/figures/tool_call_overhead.svg` — mean tool calls per task.
- `outputs/figures/invalid_action_rate.svg` — invalid actions per tool call.

To regenerate only the dataset:

```bash
python3 make_dataset.py --count 120 --seed 7 --output data/tasks.csv
```

To use a different simulation size or noise level:

```bash
python3 run_experiment.py --tasks 240 --seed 19 --noise-rate 0.18 --max-calls 8 --max-retries 2
python3 plot_results.py
```

`--tasks` with a non-default seed regenerates the CSV dataset. Keep the seed and metadata with any published results.

## Optional local Ollama experiment

This is separate from the default simulator and is not needed to generate the main results. Confirm that Ollama is running and the model is already installed, then run a small sample first:

```bash
python3 run_ollama.py --model qwen2.5:3b --tasks 8 --seed 7 --tool-failure-rate 0.10
```

You can substitute `llama3.1:8b` if that is the exact local model name reported by `ollama list`. The script calls only `http://localhost:11434/api/chat`; it does not send prompts to a paid cloud API. Model calls may take several minutes. Outputs go to `outputs/ollama/`. Increase task count only after checking runtime. Do not merge these results with the scripted-simulator results.

## Metrics and interpretation

- **Task success rate:** fraction of episodes ending closed with the expected priority, expected team, and a non-empty note.
- **Invalid action rate:** invalid tool actions divided by tool calls. A wrong but syntactically valid priority/team is a task-quality error, not necessarily a tool-schema error; the final success metric catches it.
- **Mean tool calls:** execution overhead per task.
- **Mean failed calls:** transient tool failures per task.
- **Mean gate interventions / repairs:** how often the guard blocks or repairs a proposed action.
- **Unsafe close attempts per task:** attempted closure while required fields are missing.
- **Budget exhausted rate:** fraction of episodes that hit the tool-call budget without success.

The default design uses the same task set and a stable per-action failure schedule across policy variants to make comparisons more controlled. However, it is still a synthetic benchmark with a small set of workflow rules. Use multiple seeds, vary noise and failure rates, report uncertainty intervals, and compare with other baselines before making general claims. A sensible extension is to add a second workflow, human-authored task cases, and a stronger action validator.

## Suggested student extensions

1. Add a second workflow (e.g., inventory update) and test whether results transfer.
2. Replace the scripted planner with Ollama-generated actions and compare `unguarded` with `guarded_retry`.
3. Add confidence intervals over multiple seeds and a paired statistical test.
4. Test a stricter gate that blocks instead of repairs, then compare task completion and tool-call cost.
5. Add an action budget ablation (e.g., 5, 8, and 12 calls).
6. Add a formal action schema or property-based tests for state transitions.

## Data provenance, licence, and attribution

- All ticket rows are synthetic and generated by `make_dataset.py` / `toolguard/simulator.py`.
- No external dataset, real customer data, or clinical data is used.
- Code licence: MIT (`LICENSE`).
- Generated dataset licence: CC0 1.0 (`DATA_LICENSE.txt`).
- Cite the repository/archived record that you actually publish. Do not cite a placeholder DOI; reserve a DOI in Zenodo only when you are ready to deposit a stable release.

Suggested acknowledgement: “ToolGuard synthetic ticket-triage benchmark, version 0.1.0 (2026), generated with the accompanying code and fixed seed.”

## Publication workflow

1. Run tests and experiment; retain `run_metadata.json`, `results.csv`, `summary.csv`, and SVG figures.
2. Inspect at least 10 episode rows manually and verify that the output matches the stated metric definitions.
3. Update `docs/article_draft.md` with actual results from your run. Do not write “the experiment shows” until you have run and checked it.
4. Publish the code and synthetic data in your GitHub repository; add a clear README and release tag.
5. If useful, upload `data/tasks.csv`, `outputs/summary.csv`, and figures as a Kaggle dataset/notebook. State that the data are synthetic and results are from a simulator.
6. For a citable research artifact, consider Zenodo, OSF, or Figshare. Use a versioned release and the correct licence; do not claim a DOI until the record exists.
7. Publish the article at your website: https://masmatixinnovations.co.uk/insights/ . Link to the code and data, include the research question, methods, metrics, limitations, and reproducibility command.
8. If the page is live and you have Search Console access, use URL Inspection to request indexing. This is a request, not a guarantee; indexing is not a Google certificate and may take time.
9. Use Kaggle/Hugging Face/Roboflow only when the artifact suits that platform. This project is a synthetic tabular benchmark; Kaggle is optional (a notebook and listing draft are included), Hugging Face is reasonable if you add an ML dataset/model card, and Roboflow is not appropriate because there are no images.
10. For URL inspection and indexing requests, follow Google's official Search Console guidance: https://support.google.com/webmasters/answer/9012289?hl=en&ssrid=ssr . A request is not a guarantee; Google also notes that crawling/indexing may take time and not every page is indexed: https://developers.google.com/search/docs/fundamentals/how-search-works .

## Current official UK research signals checked on 21 October 2026

- Ulster University, *Agentic AI for Complex Environments*: trust-aware agents, multi-agent process optimisation, explainable model recommendation, adaptive decisions and safety. The listed deadline is 8 January 2027; the page says overseas applicants may apply but full-time employees are not eligible for this award. Verify the page and conditions before applying: https://www.ulster.ac.uk/doctoralcollege/find-a-phd/11a-computing/1903114
- University of Glasgow, Computing Science studentships: 2027 entry; deadline 31 January 2027; the page lists £22,437/year as the UKRI stipend rate for 2027–28 in most cases and describes home/international fee support depending on studentship. Eligibility and fee coverage vary by award: https://www.gla.ac.uk/schools/computing/postgraduateresearch/prospectivestudents/scholarshipsandfundingopportunities/studentshipinformation/
- University of Glasgow, research-degree application guidance: asks applicants to demonstrate originality and rigour, and describes a research proposal structure with motivation, literature survey, methods, timeline and references: https://www.gla.ac.uk/schools/computing/postgraduateresearch/prospectivestudents/
- UCL, Foundational AI studentship: sequential decision-making, reinforcement learning, foundation models, and computational experiments; page lists £23,805/year for 2026–27 and Home tuition fees, with no fixed closing date shown at time of check: https://www.ucl.ac.uk/engineering/fully-funded-phd-studentship-foundational-ai

These are research-interest signals, not endorsements of ToolGuard and not a guarantee of funding eligibility. Because fee status, visa conditions, and scholarship rules are individual, confirm them with each university before making a decision.
