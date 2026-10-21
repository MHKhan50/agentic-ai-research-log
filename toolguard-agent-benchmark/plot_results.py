#!/usr/bin/env python3
"""Create publication-friendly SVG plots using only the Python standard library."""
import argparse
import csv
import html
from pathlib import Path

POLICY_LABELS = {
    "baseline": "Baseline",
    "retry_only": "Retry only",
    "guard_only": "Guard only",
    "guard_retry": "Guard + retry",
}


def read_summary(path):
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def make_chart(rows, metric, title, y_label, output_path, y_min=0.0, y_max=1.0):
    width, height = 900, 520
    left, right, top, bottom = 90, 30, 65, 95
    plot_w, plot_h = width - left - right, height - top - bottom
    rates = sorted({float(row["tool_failure_rate"]) for row in rows})
    policies = ["baseline", "retry_only", "guard_only", "guard_retry"]
    x_positions = {rate: left + i * plot_w / max(1, len(rates) - 1) for i, rate in enumerate(rates)}
    def y_pos(value):
        return top + (y_max - value) * plot_h / (y_max - y_min)
    pieces = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{}" height="{}" viewBox="0 0 {} {}">'.format(width, height, width, height),
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="{}" y="32" font-family="Arial,sans-serif" font-size="22" font-weight="bold" fill="#222">{}</text>'.format(left, html.escape(title)),
    ]
    for tick_i in range(6):
        value = y_min + (y_max - y_min) * tick_i / 5
        y = y_pos(value)
        pieces.append('<line x1="{}" y1="{:.1f}" x2="{}" y2="{:.1f}" stroke="#dddddd" stroke-width="1"/>'.format(left, y, width-right, y))
        tick_label = "{:.1f}".format(value) if metric == "mean_tool_calls" else "{:.0%}".format(value)
        pieces.append('<text x="{}" y="{:.1f}" text-anchor="end" dominant-baseline="middle" font-family="Arial,sans-serif" font-size="13" fill="#333">{}</text>'.format(left-12, y, tick_label))
    pieces.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#333"/>'.format(left, top, left, height-bottom))
    pieces.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="#333"/>'.format(left, height-bottom, width-right, height-bottom))
    for rate, x in x_positions.items():
        pieces.append('<text x="{:.1f}" y="{}" text-anchor="middle" font-family="Arial,sans-serif" font-size="14" fill="#333">{:.0%}</text>'.format(x, height-bottom+25, rate))
    pieces.append('<text x="{}" y="{}" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" fill="#222">Transient tool failure rate</text>'.format(left + plot_w/2, height-25))
    pieces.append('<text x="24" y="{}" transform="rotate(-90 24 {})" text-anchor="middle" font-family="Arial,sans-serif" font-size="15" fill="#222">{}</text>'.format(top+plot_h/2, top+plot_h/2, html.escape(y_label)))
    # Colours are fixed only for chart readability; this script does not alter data.
    colours = {"baseline": "#444444", "retry_only": "#2474b5", "guard_only": "#d17a00", "guard_retry": "#2a8a55"}
    for index, policy in enumerate(policies):
        selected = [row for row in rows if row["policy"] == policy]
        selected.sort(key=lambda row: float(row["tool_failure_rate"]))
        points = []
        for row in selected:
            x = x_positions[float(row["tool_failure_rate"])]
            value = float(row[metric])
            if metric in {"success_rate", "invalid_action_rate", "budget_exhausted_rate"}:
                value = max(y_min, min(y_max, value))
            points.append((x, y_pos(value)))
        if points:
            point_text = " ".join("{:.1f},{:.1f}".format(x, y) for x, y in points)
            pieces.append('<polyline points="{}" fill="none" stroke="{}" stroke-width="3"/>'.format(point_text, colours[policy]))
            for x, y in points:
                pieces.append('<circle cx="{:.1f}" cy="{:.1f}" r="5" fill="{}"/>'.format(x, y, colours[policy]))
        legend_x = left + (index % 2) * 210
        legend_y = height - 60 + (index // 2) * 22
        pieces.append('<line x1="{}" y1="{}" x2="{}" y2="{}" stroke="{}" stroke-width="3"/>'.format(legend_x, legend_y, legend_x+28, legend_y, colours[policy]))
        pieces.append('<text x="{}" y="{}" font-family="Arial,sans-serif" font-size="13" fill="#222">{}</text>'.format(legend_x+36, legend_y+4, html.escape(POLICY_LABELS[policy])))
    pieces.append('</svg>')
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text("\n".join(pieces), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", default="outputs/summary.csv")
    parser.add_argument("--output-dir", default="outputs/figures")
    args = parser.parse_args()
    rows = read_summary(args.summary)
    if not rows:
        raise SystemExit("Summary file has no rows. Run run_experiment.py first.")
    out = Path(args.output_dir)
    make_chart(rows, "success_rate", "Task completion by tool-failure rate", "Task success rate", out / "success_rate.svg")
    max_calls = max(float(row["mean_tool_calls"]) for row in rows) * 1.1
    make_chart(rows, "mean_tool_calls", "Tool-call overhead by tool-failure rate", "Mean tool calls per task", out / "tool_call_overhead.svg", 0.0, max(1.0, max_calls))
    make_chart(rows, "invalid_action_rate", "Invalid actions by tool-failure rate", "Invalid actions / tool calls", out / "invalid_action_rate.svg")
    print("SVG figures saved to {}".format(out))


if __name__ == "__main__":
    main()
