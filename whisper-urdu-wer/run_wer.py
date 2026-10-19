"""Measure Whisper word error rate on short self-recorded Urdu clinic clips.

Usage:
    python run_wer.py                      # tiny, base and small
    python run_wer.py --models small medium

Steps:
1. If a clip has no audio in data/audio/, open a reading sheet and record it.
2. Transcribe every clip with every Whisper model (faster-whisper, CPU, int8).
3. Score against data/references/ with WER, CER and clinical term recall.
4. Write results/ (CSV, transcripts, summary table, chart) and kaggle_dataset/.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from metrics import char_errors, term_recall, word_errors

ROOT = Path(__file__).resolve().parent
REF_DIR = ROOT / "data" / "references"
AUDIO_DIR = ROOT / "data" / "audio"
TERMS_FILE = ROOT / "data" / "key_terms.json"
RESULTS = ROOT / "results"
KAGGLE_DIR = ROOT / "kaggle_dataset"
READ_SHEET = ROOT / "read_aloud.html"
AUDIO_EXTS = (".wav", ".m4a", ".mp3")
DEFAULT_MODELS = ["tiny", "base", "small"]


@dataclass
class ClipResult:
    model: str
    clip: str
    audio_seconds: float
    transcribe_seconds: float
    real_time_factor: float
    ref_words: int
    substitutions: int
    deletions: int
    insertions: int
    wer: float
    cer: float
    term_recall: float
    missed_terms: str
    detected_language: str
    detected_probability: float


def load_references() -> Dict[str, str]:
    refs = {p.stem: p.read_text(encoding="utf-8").strip() for p in sorted(REF_DIR.glob("*.txt"))}
    if not refs:
        sys.exit("No reference transcripts found in data/references/.")
    return refs


def find_audio(clip: str) -> Optional[Path]:
    for ext in AUDIO_EXTS:
        path = AUDIO_DIR / (clip + ext)
        if path.exists():
            return path
    return None


def write_read_sheet(refs: Dict[str, str]) -> None:
    """A large right-to-left reading sheet, so the clips are easy to read aloud."""
    blocks = []
    for clip, text in refs.items():
        lines = "".join("<p>{}</p>".format(html.escape(line)) for line in text.splitlines())
        blocks.append("<section><h2>{}</h2>{}</section>".format(clip, lines))
    READ_SHEET.write_text(
        """<!doctype html><html lang="ur" dir="rtl"><head><meta charset="utf-8">
<title>Read aloud</title><style>
body{{font-family:"Noto Nastaliq Urdu","Geeza Pro",serif;font-size:30px;line-height:2.4;
max-width:900px;margin:24px auto;padding:0 16px;background:#fcfcfb;color:#0b0b0b}}
h2{{font-family:-apple-system,sans-serif;font-size:20px;direction:ltr;text-align:left;color:#52514e}}
section{{border-bottom:1px solid #ddd;padding-bottom:12px}}
</style></head><body>{}</body></html>""".format("".join(blocks)),
        encoding="utf-8",
    )


def ensure_recordings(refs: Dict[str, str]) -> Dict[str, Path]:
    missing = [clip for clip in refs if find_audio(clip) is None]
    if missing:
        if not sys.stdin.isatty():
            sys.exit("Missing audio for: {}. Run this script in a terminal to record.".format(", ".join(missing)))
        from recorder import record_clip

        write_read_sheet(refs)
        if sys.platform == "darwin":
            subprocess.run(["open", str(READ_SHEET)], check=False)
        print("\nRecording {} clip(s). The text is open in your browser.".format(len(missing)))
        print("Speak naturally at normal clinic speed, in a quiet room.\n")
        for clip in missing:
            print("[{}]".format(clip))
            seconds = record_clip(AUDIO_DIR / (clip + ".wav"))
            print("    Saved {:.1f} s\n".format(seconds))
    return {clip: find_audio(clip) for clip in refs}  # type: ignore[misc]


def transcribe_all(models: List[str], audio: Dict[str, Path]) -> List[Tuple[str, str, str, float, float, str, float]]:
    """Return (model, clip, text, audio_s, transcribe_s, detected_lang, prob) rows."""
    from faster_whisper import WhisperModel

    rows = []
    for name in models:
        print("Loading Whisper '{}' (first time downloads the model)...".format(name))
        model = WhisperModel(name, device="cpu", compute_type="int8")
        for clip, path in audio.items():
            # Language detection only: segments are lazy, so this is cheap.
            _, detect_info = model.transcribe(str(path), language=None)
            start = time.perf_counter()
            segments, info = model.transcribe(
                str(path),
                language="ur",
                task="transcribe",
                beam_size=5,
                temperature=0.0,
                condition_on_previous_text=False,
            )
            text = " ".join(seg.text.strip() for seg in segments)
            elapsed = time.perf_counter() - start
            rows.append(
                (name, clip, text, info.duration, elapsed, detect_info.language, detect_info.language_probability)
            )
            print("  {} {}: {:.1f} s audio in {:.1f} s".format(name, clip, info.duration, elapsed))
    return rows


def score(rows, refs: Dict[str, str], terms: Dict[str, Dict[str, List[str]]]):
    results: List[ClipResult] = []
    errors: List[Dict[str, str]] = []
    for model, clip, text, audio_s, elapsed, lang, prob in rows:
        w = word_errors(refs[clip], text)
        c = char_errors(refs[clip], text)
        recall, missed = term_recall(terms.get(clip, {}), text)
        results.append(
            ClipResult(
                model=model,
                clip=clip,
                audio_seconds=round(audio_s, 2),
                transcribe_seconds=round(elapsed, 2),
                real_time_factor=round(elapsed / audio_s, 3) if audio_s else 0.0,
                ref_words=w.ref_len,
                substitutions=w.substitutions,
                deletions=w.deletions,
                insertions=w.insertions,
                wer=round(w.rate, 4),
                cer=round(c.rate, 4),
                term_recall=round(recall, 4),
                missed_terms="; ".join(missed),
                detected_language=lang,
                detected_probability=round(prob, 3),
            )
        )
        for op, ref_tok, hyp_tok in w.alignment:
            if op != "ok":
                errors.append({"model": model, "clip": clip, "op": op, "reference": ref_tok, "hypothesis": hyp_tok})
    return results, errors


def pooled_by_model(results: List[ClipResult], rows) -> List[Dict[str, float]]:
    """Pool errors over clips (total errors / total reference words)."""
    refs = load_references()
    out = []
    for model in dict.fromkeys(r.model for r in results):
        mine = [r for r in results if r.model == model]
        texts = {clip: text for m, clip, text, *_ in rows if m == model}
        ref_words = sum(r.ref_words for r in mine)
        word_err = sum(r.substitutions + r.deletions + r.insertions for r in mine)
        char_ref = char_err = 0
        for clip, text in texts.items():
            c = char_errors(refs[clip], text)
            char_ref += c.ref_len
            char_err += c.errors
        out.append(
            {
                "model": model,
                "wer": word_err / ref_words if ref_words else 0.0,
                "cer": char_err / char_ref if char_ref else 0.0,
                "term_recall": sum(r.term_recall for r in mine) / len(mine),
                "rtf": sum(r.transcribe_seconds for r in mine) / sum(r.audio_seconds for r in mine),
                "detected_ur": sum(r.detected_language == "ur" for r in mine) / len(mine),
            }
        )
    return out


def plot(summary: List[Dict[str, float]], path: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    surface, ink, muted, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
    models = [s["model"] for s in summary]
    x = list(range(len(models)))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), facecolor=surface)
    for ax in (ax1, ax2):
        ax.set_facecolor(surface)
        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color(grid)
        ax.tick_params(colors=muted)
        ax.yaxis.grid(True, color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.set_xticks(x)
        ax.set_xticklabels(models, color=ink)

    width = 0.36
    wer = [s["wer"] * 100 for s in summary]
    cer = [s["cer"] * 100 for s in summary]
    b1 = ax1.bar([i - width / 2 - 0.01 for i in x], wer, width, color="#2a78d6", label="WER (words)")
    b2 = ax1.bar([i + width / 2 + 0.01 for i in x], cer, width, color="#eb6834", label="CER (characters)")
    ax1.bar_label(b1, fmt="%.0f%%", color=ink, fontsize=9, padding=2)
    ax1.bar_label(b2, fmt="%.0f%%", color=ink, fontsize=9, padding=2)
    ax1.set_title("Error rate (lower is better)", color=ink, loc="left", fontsize=11)
    ax1.set_ylabel("%", color=muted)
    ax1.set_ylim(0, max(wer + cer + [1.0]) * 1.3)  # headroom for labels and legend
    ax1.legend(frameon=False, labelcolor=ink)

    recall = [s["term_recall"] * 100 for s in summary]
    b3 = ax2.bar(x, recall, 0.5, color="#1baf7a")
    ax2.bar_label(b3, fmt="%.0f%%", color=ink, fontsize=9, padding=2)
    ax2.set_ylim(0, 105)
    ax2.set_title("Clinical key terms recovered (higher is better)", color=ink, loc="left", fontsize=11)

    fig.suptitle("Whisper on self-recorded Urdu clinic clips", color=ink, x=0.01, ha="left", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=160, facecolor=surface)
    plt.close(fig)


def write_outputs(results, errors, rows, summary) -> None:
    RESULTS.mkdir(exist_ok=True)
    with open(RESULTS / "results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(results[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(r) for r in results)
    with open(RESULTS / "word_errors.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["model", "clip", "op", "reference", "hypothesis"])
        writer.writeheader()
        writer.writerows(errors)
    for model, clip, text, *_ in rows:
        out = RESULTS / "transcripts" / model / (clip + ".txt")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    with open(RESULTS / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "| Model | WER | CER (no spaces) | Key terms recovered | Real-time factor | Auto-detected as Urdu |",
        "|---|---|---|---|---|---|",
    ]
    for s in summary:
        lines.append(
            "| {} | {:.1%} | {:.1%} | {:.0%} | {:.2f} | {:.0%} |".format(
                s["model"], s["wer"], s["cer"], s["term_recall"], s["rtf"], s["detected_ur"]
            )
        )
    (RESULTS / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    plot(summary, RESULTS / "wer_by_model.png")
    print("\n" + "\n".join(lines))


def export_kaggle(audio: Dict[str, Path]) -> None:
    """Folder ready to upload as a small Kaggle dataset (kept out of git)."""
    if KAGGLE_DIR.exists():
        shutil.rmtree(KAGGLE_DIR)
    (KAGGLE_DIR / "audio").mkdir(parents=True)
    for path in audio.values():
        shutil.copy2(path, KAGGLE_DIR / "audio" / path.name)
    shutil.copytree(REF_DIR, KAGGLE_DIR / "references")
    shutil.copy2(TERMS_FILE, KAGGLE_DIR / "key_terms.json")
    shutil.copytree(RESULTS / "transcripts", KAGGLE_DIR / "whisper_transcripts")
    shutil.copy2(RESULTS / "results.csv", KAGGLE_DIR / "results.csv")
    (KAGGLE_DIR / "README.md").write_text(
        "# Urdu clinic speech mini set\n\n"
        "Three short, fictional physiotherapy doctor-patient conversations in Urdu, read aloud by one "
        "adult male speaker and recorded on a MacBook microphone (16 kHz mono). Each clip has a reference "
        "transcript in Urdu script, a list of key clinical terms with accepted spellings, and Whisper "
        "transcripts (tiny, base, small) with word and character error rates.\n\n"
        "No real patient data. One speaker, read speech: useful as a smoke test, not as a benchmark.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS)
    args = parser.parse_args()

    refs = load_references()
    terms = json.loads(TERMS_FILE.read_text(encoding="utf-8"))
    audio = ensure_recordings(refs)
    rows = transcribe_all(args.models, audio)
    results, errors = score(rows, refs, terms)
    summary = pooled_by_model(results, rows)
    write_outputs(results, errors, rows, summary)
    export_kaggle(audio)
    print("\nWrote results/ and kaggle_dataset/.")


if __name__ == "__main__":
    main()
