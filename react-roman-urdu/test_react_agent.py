"""Offline tests: no Ollama needed (the LLM is a scripted fake)."""

from __future__ import annotations

import pytest

from evaluate import score
from react_agent import ClinicTools, ReActAgent, parse_step, safe_calculate


class ScriptedLLM:
    def __init__(self, turns: list[str]) -> None:
        self.turns = iter(turns)

    def __call__(self, messages, stop=None) -> str:  # noqa: ANN001
        return next(self.turns)


@pytest.fixture()
def tools() -> ClinicTools:
    return ClinicTools.from_file()


def test_parse_step_extracts_action() -> None:
    step = parse_step("Thought: need record\nAction: lookup_patient[Maryam Shafiq]")
    assert (step.thought, step.action, step.argument) == ("need record", "lookup_patient", "Maryam Shafiq")


def test_parse_step_without_action() -> None:
    assert parse_step("Mujhe lagta hai 6 sessions").action is None


def test_safe_calculate_blocks_code() -> None:
    assert safe_calculate("(10 - 4) * 2") == 12
    with pytest.raises(ValueError):
        safe_calculate("__import__('os').system('ls')")


def test_lookup_is_forgiving(tools: ClinicTools) -> None:
    assert "sports injuries" in tools.lookup_therapist("urooj")
    assert "No patient" in tools.lookup_patient("Nobody")


def test_agent_full_loop(tools: ClinicTools) -> None:
    llm = ScriptedLLM([
        "Thought: get record\nAction: lookup_patient[Maryam Shafiq]",
        "Thought: subtract\nAction: calculate[10 - 4]",
        "Thought: done\nAction: Finish[6 sessions baqi hain]",
    ])
    traj = ReActAgent(llm, tools.registry()).run("Maryam Shafiq ke kitne sessions abhi baqi hain?")
    assert traj.answer == "6 sessions baqi hain"
    assert traj.tool_calls == 2 and not traj.hit_max_steps
    assert "Observation: 6" in traj.transcript


def test_score_number_and_keywords() -> None:
    assert score("6 sessions", {"type": "number", "value": 6})
    assert not score("chhe sessions", {"type": "number", "value": 6})
    days = {"type": "keywords", "groups": [["friday", "jumma"], ["saturday", "hafta"]]}
    assert score("Jumma aur Hafta", days)
    assert not score("Friday only", days)
