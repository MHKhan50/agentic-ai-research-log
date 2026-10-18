"""Minimal ReAct agent (Yao et al., 2022) running on a local Ollama model.

Loop: the model writes ``Thought:`` + ``Action: tool[input]``; we stop generation
before it can invent an ``Observation:``, run the tool ourselves, append the real
observation, and repeat until ``Action: Finish[answer]`` or the step budget ends.
"""

from __future__ import annotations

import ast
import json
import operator
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import requests

KB_PATH = Path(__file__).with_name("clinic_kb.json")

Message = dict[str, str]


class ChatModel(Protocol):
    """Anything that maps chat messages (+ optional stop strings) to text."""

    def __call__(self, messages: list[Message], stop: list[str] | None = None) -> str: ...


@dataclass
class OllamaChat:
    """Thin client for Ollama's /api/chat endpoint (non-streaming, deterministic)."""

    model: str
    host: str = "http://localhost:11434"
    temperature: float = 0.0
    seed: int = 42
    timeout_s: float = 180.0

    def __call__(self, messages: list[Message], stop: list[str] | None = None) -> str:
        options: dict[str, Any] = {"temperature": self.temperature, "seed": self.seed}
        if stop:
            options["stop"] = stop
        resp = requests.post(
            f"{self.host}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False, "options": options},
            timeout=self.timeout_s,
        )
        resp.raise_for_status()
        return str(resp.json()["message"]["content"])


# --------------------------------------------------------------------------- tools

_BIN_OPS: dict[type[ast.operator], Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS: dict[type[ast.unaryop], Callable[[float], float]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_calculate(expression: str) -> float:
    """Evaluate arithmetic only (no names, calls or attributes) - never ``eval``."""

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large")
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported expression: {expression!r}")

    return _eval(ast.parse(expression.strip(), mode="eval"))


def _norm_name(name: str) -> str:
    name = name.strip().strip("'\"").lower()
    name = re.sub(r"^dr\.?\s*", "", name)
    return re.sub(r"\s+", " ", name)


class ClinicTools:
    """Read-only tools over the fictional clinic knowledge base."""

    def __init__(self, kb: dict[str, Any]) -> None:
        self._patients = {_norm_name(p["name"]): p for p in kb["patients"]}
        self._therapists = {_norm_name(t["name"]): t for t in kb["therapists"]}

    @classmethod
    def from_file(cls, path: Path = KB_PATH) -> ClinicTools:
        return cls(json.loads(path.read_text(encoding="utf-8")))

    @staticmethod
    def _find(table: dict[str, dict[str, Any]], query: str, kind: str) -> str:
        q = _norm_name(query)
        if q in table:
            return json.dumps(table[q], ensure_ascii=False)
        matches = [rec for key, rec in table.items() if q and (q in key or key.split()[0] == q)]
        if len(matches) == 1:
            return json.dumps(matches[0], ensure_ascii=False)
        if len(matches) > 1:
            return f"Ambiguous {kind} name '{query}'. Candidates: {[m['name'] for m in matches]}"
        return f"No {kind} found with name '{query}'."

    def lookup_patient(self, name: str) -> str:
        return self._find(self._patients, name, "patient")

    def lookup_therapist(self, name: str) -> str:
        return self._find(self._therapists, name, "therapist")

    def calculate(self, expression: str) -> str:
        try:
            value = safe_calculate(expression)
        except (ValueError, SyntaxError, ZeroDivisionError) as exc:
            return f"Calculator error: {exc}"
        return f"{value:g}" if value == int(value) else f"{value:.4f}"

    def registry(self) -> dict[str, Callable[[str], str]]:
        return {
            "lookup_patient": self.lookup_patient,
            "lookup_therapist": self.lookup_therapist,
            "calculate": self.calculate,
        }


# --------------------------------------------------------------------------- prompt

SYSTEM_PROMPT = """You are a careful clinic assistant. Solve the question by interleaving
Thought, Action and Observation steps.
Available actions:
  lookup_patient[full name]      -> the patient's record as JSON
  lookup_therapist[name]         -> the therapist's record as JSON (includes their patients)
  calculate[arithmetic]          -> the result, e.g. calculate[12 - 9]
  Finish[answer]                 -> give the final, short answer
Rules: write exactly ONE Thought and ONE Action per turn, then stop. Never write an
Observation yourself. Use only facts from Observations. The question may be in English
or Roman Urdu; give the final answer in the same language as the question."""

FEW_SHOT = """Question: How many sessions has Sara Khan done more than Ali Shah?
Thought: I need Sara Khan's record first.
Action: lookup_patient[Sara Khan]
Observation: {"name": "Sara Khan", "age": 40, "therapist": "Dr. Ali", "sessions_prescribed": 8, "sessions_done": 7}
Thought: Now I need Ali Shah's record.
Action: lookup_patient[Ali Shah]
Observation: {"name": "Ali Shah", "age": 29, "therapist": "Dr. Ali", "sessions_prescribed": 10, "sessions_done": 3}
Thought: Sara has done 7 and Ali has done 3, so I subtract.
Action: calculate[7 - 3]
Observation: 4
Thought: The difference is 4 sessions.
Action: Finish[4 sessions]

"""

_ACTION_RE = re.compile(r"Action\s*\d*\s*:\s*([A-Za-z_]+)\s*\[(.*?)\]", re.DOTALL)
_THOUGHT_RE = re.compile(r"Thought\s*\d*\s*:\s*(.*?)(?=Action\s*\d*\s*:|$)", re.DOTALL)
STOP_SEQUENCES = ["Observation:", "\nObservation"]


@dataclass(frozen=True)
class ParsedStep:
    thought: str
    action: str | None
    argument: str | None


def parse_step(text: str) -> ParsedStep:
    """Extract the first Thought / Action[arg] pair from one model turn."""
    thought_m = _THOUGHT_RE.search(text)
    action_m = _ACTION_RE.search(text)
    thought = thought_m.group(1).strip() if thought_m else ""
    if not action_m:
        return ParsedStep(thought, None, None)
    return ParsedStep(thought, action_m.group(1).strip().lower(), action_m.group(2).strip())


@dataclass
class Trajectory:
    question: str
    answer: str | None
    steps: int
    tool_calls: int
    parse_errors: int
    hit_max_steps: bool
    latency_s: float
    transcript: str


class ReActAgent:
    def __init__(
        self,
        llm: ChatModel,
        tools: dict[str, Callable[[str], str]],
        max_steps: int = 7,
        max_parse_errors: int = 2,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.max_parse_errors = max_parse_errors

    def run(self, question: str) -> Trajectory:
        start = time.perf_counter()
        scratchpad = f"Question: {question}\n"
        parse_errors = tool_calls = 0
        for step in range(1, self.max_steps + 1):
            output = self.llm(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": FEW_SHOT + scratchpad},
                ],
                stop=STOP_SEQUENCES,
            )
            parsed = parse_step(output)
            scratchpad += output.strip() + "\n"

            if parsed.action is None:
                parse_errors += 1
                if parse_errors > self.max_parse_errors:
                    return self._done(question, None, step, tool_calls, parse_errors, False, start, scratchpad)
                scratchpad += "Observation: Invalid format. Reply with 'Thought: ...' then 'Action: tool[input]'.\n"
                continue

            if parsed.action == "finish":
                return self._done(question, parsed.argument, step, tool_calls, parse_errors, False, start, scratchpad)

            tool = self.tools.get(parsed.action)
            tool_calls += 1
            observation = (
                tool(parsed.argument or "")
                if tool
                else f"Unknown action '{parsed.action}'. Use one of: {', '.join(self.tools)}, Finish."
            )
            scratchpad += f"Observation: {observation}\n"

        return self._done(question, None, self.max_steps, tool_calls, parse_errors, True, start, scratchpad)

    @staticmethod
    def _done(
        question: str,
        answer: str | None,
        steps: int,
        tool_calls: int,
        parse_errors: int,
        hit_max: bool,
        start: float,
        transcript: str,
    ) -> Trajectory:
        return Trajectory(
            question, answer, steps, tool_calls, parse_errors, hit_max, time.perf_counter() - start, transcript
        )


# --------------------------------------------------------------------------- baseline

DIRECT_PROMPT = """You are a clinic assistant. Here is the complete clinic database as JSON:
{kb}
Answer the question using only this database. Reply with ONLY the short final answer,
in the same language as the question."""


def direct_answer(llm: ChatModel, kb: dict[str, Any], question: str) -> Trajectory:
    """Baseline: whole database in the prompt, one call, no tools, no reasoning trace."""
    start = time.perf_counter()
    kb_text = json.dumps({k: v for k, v in kb.items() if not k.startswith("_")}, ensure_ascii=False)
    output = llm(
        [
            {"role": "system", "content": DIRECT_PROMPT.format(kb=kb_text)},
            {"role": "user", "content": question},
        ]
    ).strip()
    return Trajectory(question, output, 1, 0, 0, False, time.perf_counter() - start, output)


if __name__ == "__main__":
    import sys

    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:3b"
    q = sys.argv[2] if len(sys.argv) > 2 else "Ayesha Malik ke kitne sessions abhi baqi hain?"
    traj = ReActAgent(OllamaChat(model), ClinicTools.from_file().registry()).run(q)
    print(traj.transcript)
    print(f"\nANSWER: {traj.answer} | steps={traj.steps} | {traj.latency_s:.1f}s")
