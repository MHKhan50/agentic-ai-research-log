from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validator import parse_json, schema_issues, value_errors  # noqa: E402

SCHEMA = {
    "patient_id": {"type": "int"},
    "time": {"type": "str", "format": "time"},
    "urgent": {"type": "bool"},
    "body_part": {"type": "str", "enum": ["knee", "neck"]},
}
GOOD = {"patient_id": 7, "time": "14:30", "urgent": False, "body_part": "knee"}


def test_clean_object_passes() -> None:
    assert schema_issues(GOOD, SCHEMA) == []
    assert value_errors(GOOD, GOOD) == []


def test_fenced_json_is_parsed_but_not_strict() -> None:
    obj, strict = parse_json('```json\n{"a": 1}\n```')
    assert obj == {"a": 1} and strict is False
    assert parse_json('{"a": 1}') == ({"a": 1}, True)
    assert parse_json("no json here") == (None, False)


def test_bool_is_not_an_int_and_string_number_is_rejected() -> None:
    bad = dict(GOOD, patient_id=True, urgent="false")
    issues = schema_issues(bad, SCHEMA)
    assert any("patient_id" in i for i in issues)
    assert any("urgent" in i for i in issues)


def test_format_enum_missing_and_extra_keys() -> None:
    bad = {"patient_id": 7, "time": "2:30 pm", "body_part": "back", "note": "x"}
    text = " | ".join(schema_issues(bad, SCHEMA))
    assert "HH:MM" in text and "one of" in text
    assert "missing key 'urgent'" in text and "unexpected key 'note'" in text


def test_schema_valid_but_wrong_value_is_caught_only_by_truth() -> None:
    wrong = dict(GOOD, time="02:30")
    assert schema_issues(wrong, SCHEMA) == []
    assert value_errors(wrong, GOOD) == ["time"]
