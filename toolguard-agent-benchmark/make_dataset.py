#!/usr/bin/env python3
"""Generate the fully synthetic task dataset without running the benchmark."""
import argparse
from toolguard.simulator import generate_tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=120)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", default="data/tasks.csv")
    args = parser.parse_args()
    tasks = generate_tasks(args.count, args.seed, args.output)
    print("Generated {} synthetic tasks at {}".format(len(tasks), args.output))


if __name__ == "__main__":
    main()
