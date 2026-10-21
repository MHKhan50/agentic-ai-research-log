"""Label the sentences in results/review.csv one by one in the terminal.

For each sentence: type  o  (ok, supported by the transcript)  or  h  (unsupported).
For h, then type  m  (major: could change diagnosis or management) or  n  (minor).
Press Enter on an already-labelled row to keep its label. Progress is saved after every answer.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
REVIEW = HERE / "results" / "review.csv"


def ask(prompt: str, allowed: str, current: str = "") -> str:
    while True:
        ans = input(prompt).strip().lower()
        if not ans and current:
            return current
        if ans and ans[0] in allowed:
            return ans[0]


def save(rows: List[Dict[str, str]]) -> None:
    with REVIEW.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    cases = {c["id"]: c for c in json.loads((HERE / "data" / "consultations.json").read_text(encoding="utf-8"))}
    with REVIEW.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    shown = ""
    for i, r in enumerate(rows, 1):
        case_id, lang = r["note_id"].split("-")
        if r["note_id"] != shown:
            print("\n" + "=" * 70 + f"\n{r['note_id']}  TRANSCRIPT\n" + "=" * 70)
            print(cases[case_id][lang])
            shown = r["note_id"]
        print(f"\n[{i}/{len(rows)}] {r['section']}: {r['sentence']}")
        print(f"   checker: {r['auto_flag']}")
        cur = {"ok": "o", "h": "h"}.get(r["label"].strip().lower(), "")
        lab = ask("   o = ok, h = unsupported: ", "oh", cur)
        r["label"] = "ok" if lab == "o" else "H"
        if lab == "h":
            cur_sev = {"major": "m", "minor": "n"}.get(r["severity"].strip().lower(), "")
            sev = ask("   m = major, n = minor: ", "mn", cur_sev)
            r["severity"] = "major" if sev == "m" else "minor"
        else:
            r["severity"] = ""
        save(rows)
    print(f"\nAll {len(rows)} sentences labelled and saved to results/review.csv")


if __name__ == "__main__":
    main()
