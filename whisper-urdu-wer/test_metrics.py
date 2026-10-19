from __future__ import annotations

import pytest

from metrics import char_errors, term_found, term_recall, word_errors
from urdu_text import normalize_urdu


def test_normalisation_maps_arabic_letters_and_strips_punctuation() -> None:
    # Arabic yeh/kaf and a zabar diacritic should not count as errors.
    assert normalize_urdu("كيا آپ َٹھیک ہیں؟") == normalize_urdu("کیا آپ ٹھیک ہیں")
    assert normalize_urdu("درد۔ ہے، MRI!") == "درد ہے mri"


def test_perfect_transcript_has_zero_wer() -> None:
    ref = "مجھے کمر میں درد ہے۔"
    assert word_errors(ref, "مجھے کمر میں درد ہے").rate == 0.0


def test_counts_substitution_deletion_insertion() -> None:
    ref = "مجھے کمر میں درد ہے"
    hyp = "مجھے کم میں درد بہت"  # 1 substitution, then ہے -> بہت is another substitution
    counts = word_errors(ref, hyp)
    assert counts.substitutions == 2 and counts.deletions == 0 and counts.insertions == 0
    assert counts.rate == pytest.approx(2 / 5)

    counts = word_errors("کمر میں درد", "کمر درد")
    assert (counts.substitutions, counts.deletions, counts.insertions) == (0, 1, 0)

    counts = word_errors("کمر درد", "کمر میں درد")
    assert (counts.substitutions, counts.deletions, counts.insertions) == (0, 0, 1)


def test_cer_ignores_word_spacing() -> None:
    # Same letters, different spacing: CER without spaces is 0, WER is not.
    assert char_errors("فزیوتھراپی", "فزیو تھراپی").rate == 0.0
    assert word_errors("فزیوتھراپی", "فزیو تھراپی").rate > 0.0


def test_term_matching_accepts_variants_and_scripts() -> None:
    assert term_found(["ایم آر آئی", "mri"], "شاید MRI بھی کرنا پڑے")
    assert term_found(["ایم آر آئی"], "شاید ایمآرآئی بھی")
    assert not term_found(["سن"], "سنیں ڈاکٹر صاحب")  # whole words only


def test_term_recall_reports_missed_terms() -> None:
    terms = {"fever": ["بخار"], "urine": ["پیشاب"]}
    recall, missed = term_recall(terms, "بخار نہیں ہے")
    assert recall == 0.5 and missed == ["urine"]
