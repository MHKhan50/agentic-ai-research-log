"""ReAct agent (Yao et al., 2022), a direct baseline and translate-then-ReAct, on a local Ollama model.

Loop: the model writes ``Thought:`` and ``Action: tool[input]``; generation stops before it can
write an ``Observation:``; the code runs the tool and appends the real observation, until
``Action: Finish[answer]`` or the step limit.
"""

from __future__ import annotations

import ast
import json
import operator
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import requests

Message = Dict[str, str]
ChatModel = Callable[..., str]


@dataclass
class OllamaChat:
    """Ollama /api/chat client, non-streaming and deterministic."""

    model: str
    host: str = "http://localhost:11434"
    temperature: float = 0.0
    seed: int = 42
    timeout_s: float = 300.0

    def __call__(self, messages: List[Message], stop: Optional[List[str]] = None) -> str:
        options: Dict[str, Any] = {"temperature": self.temperature, "seed": self.seed}
        if stop:
            options["stop"] = stop
        resp = requests.post(f"{self.host}/api/chat",
                             json={"model": self.model, "messages": messages, "stream": False, "options": options},
                             timeout=self.timeout_s)
        resp.raise_for_status()
        return str(resp.json()["message"]["content"])


# ------------------------------------------------------------------ tools

_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Mod: operator.mod, ast.Pow: operator.pow}
_UN = {ast.USub: operator.neg, ast.UAdd: operator.pos}


def safe_calculate(expression: str) -> float:
    """Arithmetic only (no names, calls or attributes); never ``eval``."""

    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            left, right = _eval(node.left), _eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large")
            return _BIN[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UN:
            return _UN[type(node.op)](_eval(node.operand))
        raise ValueError(f"Unsupported expression: {expression!r}")

    return _eval(ast.parse(expression.strip(), mode="eval"))


def _norm(name: str) -> str:
    name = name.strip().strip("'\"").lower()
    name = re.sub(r"^dr\.?\s*", "", name)
    return re.sub(r"\s+", " ", name)


class ClinicTools:
    """Read-only lookups over one fictional clinic, plus a calculator."""

    def __init__(self, kb: Dict[str, Any]) -> None:
        self.patients = {_norm(p["name"]): p for p in kb["patients"]}
        self.therapists = {_norm(t["name"]): t for t in kb["therapists"]}

    @staticmethod
    def _find(table: Dict[str, Dict[str, Any]], query: str, kind: str) -> str:
        q = _norm(query)
        if q in table:
            return json.dumps(table[q], ensure_ascii=False)
        hits = [r for k, r in table.items() if q and (q in k or k.split()[0] == q)]
        if len(hits) == 1:
            return json.dumps(hits[0], ensure_ascii=False)
        if hits:
            return f"Ambiguous {kind} name '{query}'. Candidates: {[h['name'] for h in hits]}"
        return f"No {kind} found with name '{query}'."

    def lookup_patient(self, name: str) -> str:
        return self._find(self.patients, name, "patient")

    def lookup_therapist(self, name: str) -> str:
        return self._find(self.therapists, name, "therapist")

    def calculate(self, expression: str) -> str:
        try:
            v = safe_calculate(expression)
        except (ValueError, SyntaxError, ZeroDivisionError) as exc:
            return f"Calculator error: {exc}"
        return f"{v:g}" if v == int(v) else f"{v:.4f}"

    def registry(self) -> Dict[str, Callable[[str], str]]:
        return {"lookup_patient": self.lookup_patient, "lookup_therapist": self.lookup_therapist,
                "calculate": self.calculate}


# ------------------------------------------------------------------ prompts

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

_OBS_SARA = ('{"name": "Sara Javed", "age": 40, "therapist": "Dr. Noor", '
             '"sessions_prescribed": 8, "sessions_done": 7}')
_OBS_OMER = ('{"name": "Omer Shah", "age": 29, "therapist": "Dr. Noor", '
             '"sessions_prescribed": 10, "sessions_done": 3}')

FEW_SHOT = {
    "en": f"""Question: How many sessions has Sara Javed done more than Omer Shah?
Thought: I need Sara Javed's record first.
Action: lookup_patient[Sara Javed]
Observation: {_OBS_SARA}
Thought: Now I need Omer Shah's record.
Action: lookup_patient[Omer Shah]
Observation: {_OBS_OMER}
Thought: Sara has done 7 and Omer has done 3, so I subtract.
Action: calculate[7 - 3]
Observation: 4
Thought: The difference is 4 sessions.
Action: Finish[4 sessions]

""",
    "ru": f"""Question: Sara Javed ne Omer Shah se kitne sessions zyada kiye hain?
Thought: Pehle mujhe Sara Javed ka record chahiye.
Action: lookup_patient[Sara Javed]
Observation: {_OBS_SARA}
Thought: Ab mujhe Omer Shah ka record chahiye.
Action: lookup_patient[Omer Shah]
Observation: {_OBS_OMER}
Thought: Sara ne 7 aur Omer ne 3 sessions kiye hain, "zyada" ka matlab farq hai, is liye minus karna hai.
Action: calculate[7 - 3]
Observation: 4
Thought: Farq 4 sessions ka hai.
Action: Finish[4 sessions zyada]

""",
}

TRANSLATE_PROMPT = ("Translate the following Roman Urdu question into English. Keep every name and number exactly "
                    "as written. Reply with only the English question.")

DIRECT_PROMPT = """You are a clinic assistant. Here is the complete clinic database as JSON:
{kb}
Answer the question using only this database. Reply with ONLY the short final answer,
in the same language as the question."""

_ACTION_RE = re.compile(r"Action\s*\d*\s*:\s*([A-Za-z_]+)\s*\[(.*?)\]", re.DOTALL)
_THOUGHT_RE = re.compile(r"Thought\s*\d*\s*:\s*(.*?)(?=Action\s*\d*\s*:|$)", re.DOTALL)
STOP = ["Observation:", "\nObservation"]


def parse_step(text: str):
    t = _THOUGHT_RE.search(text)
    a = _ACTION_RE.search(text)
    thought = t.group(1).strip() if t else ""
    if not a:
        return thought, None, None
    return thought, a.group(1).strip().lower(), a.group(2).strip()


@dataclass
class Trajectory:
    answer: Optional[str]
    steps: int = 0
    lookups: int = 0
    calc_exprs: List[str] = field(default_factory=list)
    parse_errors: int = 0
    hit_max_steps: bool = False
    latency_s: float = 0.0
    transcript: str = ""
    translation: Optional[str] = None


def react(llm: ChatModel, tools: Dict[str, Callable[[str], str]], question: str, shot: str = "en",
          max_steps: int = 8, max_parse_errors: int = 2) -> Trajectory:
    """ReAct as a multi-turn chat: the model's steps are assistant turns, observations are user turns.

    An earlier version resent the whole scratchpad inside one user message. llama3.2:3b then restarted
    from the first step on every turn and looped until the step limit, so the protocol, not the
    language, decided its score. Separate turns are the usual chat-model format and fair to all models.
    """
    start = time.perf_counter()
    pad = f"Question: {question}\n"
    messages: List[Message] = [{"role": "system", "content": SYSTEM_PROMPT},
                               {"role": "user", "content": FEW_SHOT[shot] + pad}]
    tr = Trajectory(answer=None)
    for step in range(1, max_steps + 1):
        tr.steps = step
        out = llm(messages, stop=STOP)
        _, action, arg = parse_step(out)
        messages.append({"role": "assistant", "content": out.strip()})
        pad += out.strip() + "\n"
        if action is None:
            tr.parse_errors += 1
            if tr.parse_errors > max_parse_errors:
                break
            obs_text = "Observation: Invalid format. Reply with 'Thought: ...' then 'Action: tool[input]'."
            messages.append({"role": "user", "content": obs_text})
            pad += obs_text + "\n"
            continue
        if action == "finish":
            tr.answer = arg
            break
        tool = tools.get(action)
        if action in ("lookup_patient", "lookup_therapist"):
            tr.lookups += 1
        if action == "calculate":
            tr.calc_exprs.append(arg or "")
        obs = tool(arg or "") if tool else f"Unknown action '{action}'. Use one of: {', '.join(tools)}, Finish."
        messages.append({"role": "user", "content": f"Observation: {obs}"})
        pad += f"Observation: {obs}\n"
    else:
        tr.hit_max_steps = True
    tr.latency_s = time.perf_counter() - start
    tr.transcript = pad
    return tr


def direct(llm: ChatModel, kb: Dict[str, Any], question: str) -> Trajectory:
    start = time.perf_counter()
    kb_text = json.dumps({k: v for k, v in kb.items() if not k.startswith("_")}, ensure_ascii=False)
    out = llm([{"role": "system", "content": DIRECT_PROMPT.format(kb=kb_text)},
               {"role": "user", "content": question}]).strip()
    return Trajectory(answer=out, steps=1, latency_s=time.perf_counter() - start, transcript=out)


def translate_then_react(llm: ChatModel, tools: Dict[str, Callable[[str], str]], question: str,
                         max_steps: int = 8) -> Trajectory:
    start = time.perf_counter()
    lines = [ln.strip() for ln in llm([{"role": "system", "content": TRANSLATE_PROMPT},
                                       {"role": "user", "content": question}]).strip().splitlines() if ln.strip()]
    english = lines[0].strip('"') if lines else question
    tr = react(llm, tools, english, shot="en", max_steps=max_steps)
    tr.translation = english
    tr.latency_s = time.perf_counter() - start
    return tr
