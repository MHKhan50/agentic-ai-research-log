"""Run ReAct vs direct-context baseline on English and Roman Urdu questions.

Usage:
    python run_experiment.py --model qwen2.5:3b
    python run_experiment.py --model qwen2.5:3b --limit 2   # quick smoke test
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from evaluate import score  # noqa: E402
from react_agent import KB_PATH, ClinicTools, OllamaChat, ReActAgent, direct_answer  # noqa: E402

HERE = Path(__file__).parent
LANGS = {"en": "English", "roman_urdu": "Roman Urdu"}
COLORS = {"English": "#2a78d6", "Roman Urdu": "#eb6834"}  # validated categorical slots 1-2


def check_ollama(host: str, model: str) -> None:
    try:
        tags = requests.get(f"{host}/api/tags", timeout=5).json()
    except requests.RequestException:
        sys.exit(f"Ollama not reachable at {host}. Start it with: ollama serve")
    names = {m["name"] for m in tags.get("models", [])}
    if model not in names and f"{model}:latest" not in names:
        sys.exit(f"Model '{model}' not pulled. Run: ollama pull {model}")


def plot_accuracy(summary: pd.DataFrame, model: str, out: Path) -> None:
    methods = list(summary["method"].unique())
    fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
    width = 0.36
    for i, lang in enumerate(LANGS.values()):
        sub = summary[summary["language"] == lang].set_index("method").reindex(methods)
        xs = [m + (i - 0.5) * (width + 0.02) for m in range(len(methods))]
        bars = ax.bar(xs, sub["accuracy"] * 100, width, color=COLORS[lang], label=lang)
        for bar, n_ok, n in zip(bars, sub["n_correct"], sub["n"]):
            ax.annotate(f"{int(n_ok)}/{int(n)}", (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        ha="center", va="bottom", fontsize=9, color="#52514e", xytext=(0, 2),
                        textcoords="offset points")
    ax.set_xticks(range(len(methods)), methods)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Accuracy (%)")
    ax.set_title(f"English vs Roman Urdu - {model}", loc="left", fontsize=11)
    ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--max-steps", type=int, default=7)
    parser.add_argument("--limit", type=int, default=None, help="only first N questions")
    args = parser.parse_args()

    check_ollama(args.host, args.model)
    kb = json.loads(KB_PATH.read_text(encoding="utf-8"))
    questions = json.loads((HERE / "questions.json").read_text(encoding="utf-8"))[: args.limit]
    llm = OllamaChat(args.model, host=args.host)
    agent = ReActAgent(llm, ClinicTools(kb).registry(), max_steps=args.max_steps)

    out_dir = HERE / "results" / args.model.replace(":", "_").replace("/", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    with (out_dir / "trajectories.jsonl").open("w", encoding="utf-8") as traj_file:
        for q in questions:
            for lang_key, lang in LANGS.items():
                for method in ("ReAct", "Direct (KB in prompt)"):
                    traj = agent.run(q[lang_key]) if method == "ReAct" else direct_answer(llm, kb, q[lang_key])
                    ok = score(traj.answer, q["gold"])
                    row = {"id": q["id"], "hops": q["hops"], "language": lang, "method": method,
                           "correct": ok, **{k: v for k, v in asdict(traj).items() if k != "transcript"}}
                    rows.append(row)
                    traj_file.write(json.dumps({**row, "transcript": traj.transcript}, ensure_ascii=False) + "\n")
                    print(f"{q['id']} {lang:<10} {method:<22} {'OK ' if ok else 'BAD'} -> {traj.answer!r}")

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "results.csv", index=False)
    summary = (
        df.groupby(["method", "language"])
        .agg(n=("correct", "size"), n_correct=("correct", "sum"), accuracy=("correct", "mean"),
             avg_steps=("steps", "mean"), parse_error_rate=("parse_errors", lambda s: (s > 0).mean()),
             max_steps_rate=("hit_max_steps", "mean"), median_latency_s=("latency_s", "median"))
        .reset_index()
        .round(3)
    )
    summary.to_csv(out_dir / "summary.csv", index=False)
    plot_accuracy(summary, args.model, out_dir / "accuracy_chart.png")
    print("\n" + summary.to_string(index=False))
    print(f"\nSaved to {out_dir}")


if __name__ == "__main__":
    main()
