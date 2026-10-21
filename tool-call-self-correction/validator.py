"""Schema and value checks for tool-call JSON produced by a language model.

Two separate questions are answered here:

* ``schema_issues``: what a real validator could know (keys, types, formats,
  enums, ranges). Only these issues are fed back to the model.
* ``value_errors``: comparison with the ground truth. A real system does not
  know these, so they are never shown to the model.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

TYPE_NAMES = {"int": "integer", "float": "number", "str": "string", "bool": "boolean"}
FORMATS = {
    "date": (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "YYYY-MM-DD"),
    "time": (re.compile(r"^\d{2}:\d{2}$"), "HH:MM (24-hour)"),
}
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json(raw: str) -> Tuple[Optional[Dict[str, Any]], bool]:
    """Return (object, strict_ok).

    strict_ok is True only when ``raw`` is exactly one JSON object. If it is
    not, a lenient fallback strips code fences or takes the first {...} block,
    so wrapped answers can still be scored, but the strict failure is recorded.
    """
    text = raw.strip()
    try:
        obj = json.loads(text)
        return (obj, True) if isinstance(obj, dict) else (None, False)
    except ValueError:
        pass
    candidates = [_FENCE.sub("", text)]
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        candidates.append(text[start : end + 1])
    for cand in candidates:
        try:
            obj = json.loads(cand)
        except ValueError:
            continue
        if isinstance(obj, dict):
            return obj, False
    return None, False


def _type_ok(value: Any, type_name: str) -> bool:
    # bool is a subclass of int in Python, so it is excluded explicitly.
    if type_name == "bool":
        return isinstance(value, bool)
    if isinstance(value, bool):
        return False
    if type_name == "int":
        return isinstance(value, int)
    if type_name == "float":
        return isinstance(value, (int, float))
    if type_name == "str":
        return isinstance(value, str)
    raise ValueError(f"unknown type {type_name!r}")


def schema_issues(obj: Optional[Dict[str, Any]], schema: Dict[str, Dict[str, Any]]) -> List[str]:
    """List problems a schema validator can detect without knowing the truth."""
    if obj is None:
        return ["output is not a JSON object"]
    issues: List[str] = []
    for key, spec in schema.items():
        if key not in obj:
            issues.append(f"missing key '{key}'")
            continue
        value = obj[key]
        if not _type_ok(value, spec["type"]):
            issues.append(f"'{key}' must be a {TYPE_NAMES[spec['type']]}, got {json.dumps(value)}")
            continue
        fmt = spec.get("format")
        if fmt and not FORMATS[fmt][0].match(value):
            issues.append(f"'{key}' must use format {FORMATS[fmt][1]}, got {json.dumps(value)}")
        if "enum" in spec and value not in spec["enum"]:
            issues.append(f"'{key}' must be one of {spec['enum']}, got {json.dumps(value)}")
        if "min" in spec and value < spec["min"]:
            issues.append(f"'{key}' must be >= {spec['min']}")
        if "max" in spec and value > spec["max"]:
            issues.append(f"'{key}' must be <= {spec['max']}")
    for key in obj:
        if key not in schema:
            issues.append(f"unexpected key '{key}'")
    return issues


def _norm(value: Any) -> Any:
    if isinstance(value, str):
        return re.sub(r"[^a-z0-9:\-]", "", value.lower())
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def value_errors(obj: Optional[Dict[str, Any]], expected: Dict[str, Any]) -> List[str]:
    """Keys whose value differs from the ground truth (case and punctuation ignored)."""
    if obj is None:
        return list(expected)
    wrong = []
    for key, truth in expected.items():
        got = obj.get(key)
        if isinstance(truth, bool) or isinstance(got, bool):
            same = got is truth
        else:
            same = _norm(got) == _norm(truth)
        if not same:
            wrong.append(key)
    return wrong
