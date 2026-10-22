"""Small, deterministic synthetic benchmark for agent-memory provenance policies.

Python 3.9+; standard library only. This is a simulator, not an LLM evaluation.
"""
import csv
import math
import random
from pathlib import Path

POLICIES = ("baseline_relevance", "provenance_filter", "provenance_plus_corroboration")
POISON_RATES = (0.0, 0.10, 0.25)
SEEDS = (7, 13, 29)
TASKS_PER_SEED_RATE = 250

SCENARIO_FIELDS = [
    "scenario_id", "seed", "task_index", "poisoning_rate", "poison_present",
    "primary_clean_relevance", "primary_clean_trust", "primary_clean_corroboration",
    "secondary_clean_relevance", "secondary_clean_trust", "secondary_clean_corroboration",
    "poison_relevance", "poison_trust", "poison_corroboration",
    "expected_memory_id", "poisoned_memory_id", "scenario_note",
]
RESULT_FIELDS = [
    "scenario_id", "seed", "poisoning_rate", "policy", "poison_present",
    "selected_memory_id", "selected_memory_is_poisoned", "task_success",
    "attack_success", "abstained", "candidates_considered",
]
SUMMARY_FIELDS = [
    "poisoning_rate", "policy", "n_episodes", "n_poisoned_episodes",
    "attack_success_rate_on_poisoned", "unsafe_action_rate_overall",
    "benign_task_success_rate", "overall_task_success_rate", "abstention_rate",
    "mean_candidates_considered",
]


def _candidate(memory_id, relevance, trust, corroboration, poisoned=False):
    return {
        "memory_id": memory_id,
        "relevance": relevance,
        "trust": trust,
        "corroboration": corroboration,
        "poisoned": poisoned,
    }


def generate_scenarios():
    """Generate controlled synthetic memory-retrieval scenarios."""
    rows = []
    for seed in SEEDS:
        for rate in POISON_RATES:
            rng = random.Random(seed * 1000 + int(rate * 10000))
            for task_index in range(TASKS_PER_SEED_RATE):
                poison_present = rng.random() < rate
                primary_corr = 1 if rng.random() < 0.08 else rng.choice((2, 2, 3))
                secondary_corr = rng.choice((2, 2, 3))
                primary_rel = round(rng.uniform(0.62, 0.82), 4)
                secondary_rel = round(rng.uniform(0.20, 0.52), 4)
                poison_rel = round(rng.uniform(0.60, 0.98), 4) if poison_present else ""
                if poison_present:
                    # Most injected entries are visibly low-trust; a minority are
                    # mistakenly assigned high provenance trust to test layered defence.
                    poison_trust = round(rng.uniform(0.25, 0.65), 4) if rng.random() < 0.75 else round(rng.uniform(0.72, 0.95), 4)
                    poison_corr = 1
                else:
                    poison_trust = ""
                    poison_corr = ""
                scenario_id = "s{:02d}_r{:02d}_t{:04d}".format(seed, int(rate * 100), task_index)
                rows.append({
                    "scenario_id": scenario_id,
                    "seed": seed,
                    "task_index": task_index,
                    "poisoning_rate": rate,
                    "poison_present": int(poison_present),
                    "primary_clean_relevance": primary_rel,
                    "primary_clean_trust": round(rng.uniform(0.82, 0.99), 4),
                    "primary_clean_corroboration": primary_corr,
                    "secondary_clean_relevance": secondary_rel,
                    "secondary_clean_trust": round(rng.uniform(0.80, 0.99), 4),
                    "secondary_clean_corroboration": secondary_corr,
                    "poison_relevance": poison_rel,
                    "poison_trust": poison_trust,
                    "poison_corroboration": poison_corr,
                    "expected_memory_id": "clean_primary",
                    "poisoned_memory_id": "poisoned_instruction" if poison_present else "",
                    "scenario_note": "Synthetic only; poisoned instruction is represented as a label, not executed.",
                })
    return rows


def _build_candidates(row):
    candidates = [
        _candidate("clean_primary", float(row["primary_clean_relevance"]), float(row["primary_clean_trust"]), int(row["primary_clean_corroboration"])),
        _candidate("clean_secondary", float(row["secondary_clean_relevance"]), float(row["secondary_clean_trust"]), int(row["secondary_clean_corroboration"])),
    ]
    if int(row["poison_present"]):
        candidates.append(_candidate("poisoned_instruction", float(row["poison_relevance"]), float(row["poison_trust"]), int(row["poison_corroboration"]), True))
    return candidates


def evaluate_scenario(row, policy):
    """Evaluate one scenario under a named policy without executing any action."""
    candidates = _build_candidates(row)
    if policy == "baseline_relevance":
        eligible = candidates
    elif policy == "provenance_filter":
        eligible = [c for c in candidates if c["trust"] >= 0.70]
    elif policy == "provenance_plus_corroboration":
        eligible = [c for c in candidates if c["trust"] >= 0.70 and c["corroboration"] >= 2]
    else:
        raise ValueError("Unknown policy: {}".format(policy))

    # Candidate ordering is deterministic: relevance descending, then memory ID.
    eligible = sorted(eligible, key=lambda c: (-c["relevance"], c["memory_id"]))
    selected = eligible[0] if eligible else None
    selected_id = selected["memory_id"] if selected else "ABSTAIN"
    selected_poisoned = int(bool(selected and selected["poisoned"]))
    task_success = int(selected_id == "clean_primary")
    attack_success = int(selected_poisoned)
    return {
        "scenario_id": row["scenario_id"],
        "seed": row["seed"],
        "poisoning_rate": row["poisoning_rate"],
        "policy": policy,
        "poison_present": row["poison_present"],
        "selected_memory_id": selected_id,
        "selected_memory_is_poisoned": selected_poisoned,
        "task_success": task_success,
        "attack_success": attack_success,
        "abstained": int(selected is None),
        "candidates_considered": len(eligible),
    }


def run_experiment(scenarios):
    return [evaluate_scenario(s, p) for s in scenarios for p in POLICIES]


def _rate(numerator, denominator):
    return round(float(numerator) / denominator, 6) if denominator else "NA"


def summarize(results):
    summaries = []
    rates = POISON_RATES
    for rate in rates:
        for policy in POLICIES:
            subset = [r for r in results if float(r["poisoning_rate"]) == rate and r["policy"] == policy]
            poisoned = [r for r in subset if int(r["poison_present"]) == 1]
            benign = [r for r in subset if int(r["poison_present"]) == 0]
            summaries.append({
                "poisoning_rate": rate,
                "policy": policy,
                "n_episodes": len(subset),
                "n_poisoned_episodes": len(poisoned),
                "attack_success_rate_on_poisoned": _rate(sum(int(r["attack_success"]) for r in poisoned), len(poisoned)),
                "unsafe_action_rate_overall": _rate(sum(int(r["attack_success"]) for r in subset), len(subset)),
                "benign_task_success_rate": _rate(sum(int(r["task_success"]) for r in benign), len(benign)),
                "overall_task_success_rate": _rate(sum(int(r["task_success"]) for r in subset), len(subset)),
                "abstention_rate": _rate(sum(int(r["abstained"]) for r in subset), len(subset)),
                "mean_candidates_considered": round(sum(int(r["candidates_considered"]) for r in subset) / len(subset), 4) if subset else "NA",
            })
    return summaries



def summarize_by_seed(results):
    """Return the same metrics separately for each seed and condition."""
    rows = []
    for seed in SEEDS:
        seed_results = [r for r in results if int(r["seed"]) == seed]
        for row in summarize(seed_results):
            row = dict(row)
            row["seed"] = seed
            rows.append(row)
    return rows


def write_csv(path, rows, fields):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_svg(path, summaries, metric, title, y_label, max_y=1.0):
    """Write a dependency-free SVG line plot."""
    width, height = 900, 540
    left, right, top, bottom = 90, 35, 70, 80
    plot_w, plot_h = width - left - right, height - top - bottom
    rates = list(POISON_RATES)
    colors = {
        "baseline_relevance": "#3366cc",
        "provenance_filter": "#dc3912",
        "provenance_plus_corroboration": "#109618",
    }
    def x_at(i):
        return left + (plot_w * i / max(1, len(rates) - 1))
    def y_at(value):
        return top + plot_h * (1.0 - max(0.0, min(max_y, float(value))) / max_y)
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">'.format(width, height, width, height),
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="{}" y="35" font-size="22" font-family="Arial" font-weight="bold">{}</text>'.format(left, title),
    ]
    for tick in range(0, 6):
        value = max_y * tick / 5
        y = y_at(value)
        pieces.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#dddddd" stroke-width="1"/>'.format(left, y, width-right, y))
        pieces.append('<text x="{}" y="{}" text-anchor="end" font-size="13" font-family="Arial">{:.0%}</text>'.format(left-12, y+5, value))
    for i, rate in enumerate(rates):
        x = x_at(i)
        pieces.append('<text x="{}" y="{}" text-anchor="middle" font-size="14" font-family="Arial">{:.0%}</text>'.format(x, height-bottom+28, rate))
    pieces.append('<text x="{}" y="{}" text-anchor="middle" font-size="15" font-family="Arial">Injected-memory scenario rate</text>'.format(left+plot_w/2, height-22))
    pieces.append('<text x="25" y="{}" transform="rotate(-90 25 {})" text-anchor="middle" font-size="15" font-family="Arial">{}</text>'.format(top+plot_h/2, top+plot_h/2, y_label))
    for policy in POLICIES:
        points = []
        for i, rate in enumerate(rates):
            row = next(r for r in summaries if float(r["poisoning_rate"]) == rate and r["policy"] == policy)
            val = row[metric]
            if val == "NA":
                continue
            points.append((x_at(i), y_at(float(val))))
        if points:
            pts = " ".join("{:.1f},{:.1f}".format(x,y) for x,y in points)
            pieces.append('<polyline points="{}" fill="none" stroke="{}" stroke-width="3"/>'.format(pts, colors[policy]))
            for x,y in points:
                pieces.append('<circle cx="{:.1f}" cy="{:.1f}" r="5" fill="{}"/>'.format(x,y,colors[policy]))
    legend_y = height - 54
    legend_x = left
    for i, policy in enumerate(POLICIES):
        x = legend_x + i * 255
        pieces.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="3"/>'.format(x, legend_y, x+25, legend_y, colors[policy]))
        pieces.append('<text x="{}" y="{}" font-size="12" font-family="Arial">{}</text>'.format(x+32, legend_y+4, policy.replace("_", " ")))
    pieces.append('</svg>')
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(pieces), encoding="utf-8")
