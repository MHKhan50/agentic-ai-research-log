"""Error metrics for speech recognition: WER, CER and clinical term recall."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Tuple

from urdu_text import normalize_urdu, words

# One alignment step: (operation, reference token, hypothesis token).
# operation is "ok", "sub", "del" or "ins".
AlignStep = Tuple[str, str, str]


@dataclass
class ErrorCounts:
    ref_len: int
    substitutions: int
    deletions: int
    insertions: int
    alignment: List[AlignStep] = field(default_factory=list)

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def rate(self) -> float:
        """Error rate; can exceed 1.0 when the hypothesis has many insertions."""
        if self.ref_len == 0:
            return 0.0 if self.errors == 0 else float("inf")
        return self.errors / self.ref_len


def align(ref: Sequence[str], hyp: Sequence[str]) -> ErrorCounts:
    """Levenshtein alignment with a backtrace that counts S, D and I."""
    n, m = len(ref), len(hyp)
    dist = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dist[i][0] = i
    for j in range(1, m + 1):
        dist[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dist[i][j] = min(
                dist[i - 1][j - 1] + cost,  # match / substitution
                dist[i - 1][j] + 1,  # deletion
                dist[i][j - 1] + 1,  # insertion
            )

    steps: List[AlignStep] = []
    subs = dels = ins = 0
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            if dist[i][j] == dist[i - 1][j - 1] + cost:
                if cost:
                    subs += 1
                    steps.append(("sub", ref[i - 1], hyp[j - 1]))
                else:
                    steps.append(("ok", ref[i - 1], hyp[j - 1]))
                i, j = i - 1, j - 1
                continue
        if i > 0 and dist[i][j] == dist[i - 1][j] + 1:
            dels += 1
            steps.append(("del", ref[i - 1], ""))
            i -= 1
        else:
            ins += 1
            steps.append(("ins", "", hyp[j - 1]))
            j -= 1
    steps.reverse()
    return ErrorCounts(n, subs, dels, ins, steps)


def word_errors(reference: str, hypothesis: str) -> ErrorCounts:
    """Word-level errors after Urdu normalisation."""
    return align(words(reference), words(hypothesis))


def char_errors(reference: str, hypothesis: str) -> ErrorCounts:
    """Character-level errors with spaces removed.

    Urdu word boundaries are written inconsistently (e.g. "فزیوتھراپی" vs
    "فزیو تھراپی"), so CER without spaces separates spelling errors from
    spacing choices.
    """
    ref_chars = list(normalize_urdu(reference).replace(" ", ""))
    hyp_chars = list(normalize_urdu(hypothesis).replace(" ", ""))
    counts = align(ref_chars, hyp_chars)
    counts.alignment = []  # character alignment is too long to be useful
    return counts


def term_found(variants: Sequence[str], hypothesis: str) -> bool:
    """True if any spelling variant of a key term appears in the hypothesis.

    Matching is on normalised text, with and without spaces, so both Urdu
    script and Latin spellings (e.g. "ایم آر آئی" / "MRI") can be accepted.
    """
    hyp = normalize_urdu(hypothesis)
    hyp_padded = " " + hyp + " "
    hyp_nospace = hyp.replace(" ", "")
    for variant in variants:
        v = normalize_urdu(variant)
        if not v:
            continue
        if (" " + v + " ") in hyp_padded:
            return True
        if " " in v and v.replace(" ", "") in hyp_nospace:
            return True
    return False


def term_recall(terms: Dict[str, List[str]], hypothesis: str) -> Tuple[float, List[str]]:
    """Share of key clinical terms recovered, and the list of missed terms."""
    if not terms:
        return 1.0, []
    missed = [name for name, variants in terms.items() if not term_found(variants, hypothesis)]
    return 1.0 - len(missed) / len(terms), missed
