#!/usr/bin/env python3
"""Run the dependency-free ToolGuard synthetic benchmark."""
import argparse
import json
from pathlib import Path

from toolguard.simulator import (
    environment_metadata,
    generate_tasks,
    load_tasks,
    run_experiment,
    write_csv,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=int, default=120, help="Number of synthetic tickets (default: 120).")
    parser.add_argument("--seed", type=int, default=7, help="Reproducible random seed (default: 7).")
    parser.add_argument("--noise-rate", type=float, default=0.12, help="Per-plan argument/order noise (default: 0.12).")
    parser.add_argument("--max-calls", type=int, default=8, help="Tool-call budget per episode (default: 8).")
    parser.add_argument("--max-retries", type=int, default=2, help="Retries after the first attempt (default: 2).")
    parser.add_argument("--data", default="data/tasks.csv", help="Existing task CSV; if absent, generate it.")
    parser.add_argument("--output-dir", default="outputs", help="Output directory (default: outputs).")
    args = parser.parse_args()
    if args.tasks < 1:
        parser.error("--tasks must be >= 1")
    if not 0 <= args.noise_rate <= 1:
        parser.error("--noise-rate must be between 0 and 1")
    output_dir = Path(args.output_dir)
    data_path = Path(args.data)
    if data_path.exists() and args.tasks == 120 and args.seed == 7:
        tasks = load_tasks(data_path, limit=args.tasks)
    else:
        tasks = generate_tasks(args.tasks, seed=args.seed, output_path=data_path)
    failure_rates = (0.0, 0.10, 0.25)
    rows, summary = run_experiment(
        tasks, failure_rates=failure_rates, noise_rate=args.noise_rate,
        seed=args.seed, max_calls=args.max_calls, max_retries=args.max_retries,
    )
    write_csv(output_dir / "results.csv", rows)
    write_csv(output_dir / "summary.csv", summary)
    metadata = environment_metadata(args.seed, len(tasks), args.noise_rate,
                                   failure_rates, args.max_calls, args.max_retries)
    (output_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("ToolGuard run complete")
    print("Tasks: {} | policies: 4 | failure rates: {}".format(len(tasks), ", ".join(str(x) for x in failure_rates)))
    print("Episode rows: {}".format(len(rows)))
    print("Results: {}".format(output_dir / "results.csv"))
    print("Summary: {}".format(output_dir / "summary.csv"))
    for row in summary:
        print("{:<12} failure={:.2f} success={:.1%} invalid-action={:.1%} mean-calls={:.2f}".format(
            row["policy"], row["tool_failure_rate"], row["success_rate"],
            row["invalid_action_rate"], row["mean_tool_calls"],
        ))


if __name__ == "__main__":
    main()
