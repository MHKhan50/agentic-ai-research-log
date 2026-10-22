#!/usr/bin/env python3
"""Run the MemTrust-Lite synthetic agent-memory benchmark (Python 3.9+)."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
from memtrust import (SCENARIO_FIELDS, RESULT_FIELDS, SUMMARY_FIELDS, generate_scenarios,
                      run_experiment, summarize, summarize_by_seed, write_csv, make_svg)


def main():
    scenarios = generate_scenarios()
    results = run_experiment(scenarios)
    summaries = summarize(results)
    seed_summaries = summarize_by_seed(results)
    write_csv(ROOT / "data" / "scenarios.csv", scenarios, SCENARIO_FIELDS)
    write_csv(ROOT / "outputs" / "results.csv", results, RESULT_FIELDS)
    write_csv(ROOT / "outputs" / "summary.csv", summaries, SUMMARY_FIELDS)
    write_csv(ROOT / "outputs" / "seed_summary.csv", seed_summaries, ["seed"] + SUMMARY_FIELDS)
    make_svg(ROOT / "outputs" / "attack_success_rate.svg", summaries,
             "attack_success_rate_on_poisoned", "Memory poisoning: attack success among poisoned episodes",
             "Attack success rate", 1.0)
    make_svg(ROOT / "outputs" / "benign_task_success.svg", summaries,
             "benign_task_success_rate", "Utility on clean-only episodes",
             "Benign task success rate", 1.0)
    make_svg(ROOT / "outputs" / "overall_task_success.svg", summaries,
             "overall_task_success_rate", "Overall task success under synthetic memory poisoning",
             "Overall task success rate", 1.0)
    print("MemTrust-Lite complete (synthetic simulator; no LLM calls).")
    print("Scenarios: {} | policy episodes: {}".format(len(scenarios), len(results)))
    print("Outputs: data/scenarios.csv, outputs/results.csv, outputs/summary.csv, outputs/seed_summary.csv, outputs/*.svg")
    print("\nSummary (rates are proportions; NA means no poisoned cases were sampled):")
    for row in summaries:
        print("rate={:.0%} policy={} attack={} benign={} overall={} abstain={}".format(
            float(row["poisoning_rate"]), row["policy"], row["attack_success_rate_on_poisoned"],
            row["benign_task_success_rate"], row["overall_task_success_rate"], row["abstention_rate"]))

if __name__ == "__main__":
    main()
