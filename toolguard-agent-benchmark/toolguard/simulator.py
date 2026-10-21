"""Synthetic ticket workflow and reproducible policy benchmark.

This is a controlled simulator, not a real customer-support system and not an
LLM performance claim. It deliberately separates tool failures from argument
noise so that validation/retry policies can be studied independently.
"""

import csv
import hashlib
import json
import random
import sys
from pathlib import Path

PRIORITY_BY_SEVERITY = {
    "low": "low",
    "medium": "normal",
    "high": "high",
    "critical": "urgent",
}
TEAM_BY_CATEGORY = {
    "billing": "billing",
    "technical": "engineering",
    "account": "identity",
    "safety": "trust_safety",
}
VALID_PRIORITIES = tuple(sorted(set(PRIORITY_BY_SEVERITY.values())))
VALID_TEAMS = tuple(sorted(set(TEAM_BY_CATEGORY.values())))
CATEGORIES = tuple(TEAM_BY_CATEGORY.keys())
SEVERITIES = tuple(PRIORITY_BY_SEVERITY.keys())


def stable_seed(*parts):
    """Return a stable integer seed independent of Python's hash randomisation."""
    raw = "|".join(str(part) for part in parts).encode("utf-8")
    return int(hashlib.sha256(raw).hexdigest()[:16], 16)


def generate_tasks(count=120, seed=7, output_path=None):
    """Generate a balanced, fully synthetic ticket dataset and optionally save it."""
    if count < 1:
        raise ValueError("count must be at least 1")
    rng = random.Random(seed)
    combos = [(category, severity) for category in CATEGORIES for severity in SEVERITIES]
    rng.shuffle(combos)
    tasks = []
    for index in range(count):
        category, severity = combos[index % len(combos)]
        ticket_id = "SYN-{:04d}".format(index + 1)
        scenario = "Synthetic {} ticket with {} severity.".format(category, severity)
        tasks.append({
            "ticket_id": ticket_id,
            "category": category,
            "severity": severity,
            "expected_priority": PRIORITY_BY_SEVERITY[severity],
            "expected_team": TEAM_BY_CATEGORY[category],
            "scenario_text": scenario,
        })
    if output_path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(tasks[0].keys()))
            writer.writeheader()
            writer.writerows(tasks)
    return tasks


def load_tasks(path, limit=None):
    with Path(path).open("r", newline="", encoding="utf-8") as handle:
        tasks = list(csv.DictReader(handle))
    if limit is not None:
        tasks = tasks[:limit]
    return tasks


def make_noisy_plan(task, seed=7, noise_rate=0.12):
    """Create a transparent scripted plan with controlled argument/order noise."""
    if not 0.0 <= noise_rate <= 1.0:
        raise ValueError("noise_rate must be between 0 and 1")
    rng = random.Random(stable_seed(seed, task["ticket_id"], "plan"))
    plan = [
        {"action": "inspect_ticket"},
        {"action": "set_priority", "priority": task["expected_priority"]},
        {"action": "assign_team", "team": task["expected_team"]},
        {"action": "add_note", "note": "Reviewed synthetic ticket and selected the appropriate team."},
        {"action": "close_ticket"},
    ]
    if rng.random() < noise_rate:
        alternatives = [value for value in VALID_PRIORITIES if value != task["expected_priority"]]
        plan[1]["priority"] = rng.choice(alternatives)
    if rng.random() < noise_rate:
        alternatives = [value for value in VALID_TEAMS if value != task["expected_team"]]
        plan[2]["team"] = rng.choice(alternatives)
    if rng.random() < noise_rate:
        plan[3]["note"] = ""
    if rng.random() < noise_rate:
        # Deliberately propose closure before the note; this tests prerequisite gating.
        plan[3], plan[4] = plan[4], plan[3]
    return plan


class TicketEnvironment:
    """Minimal synthetic tool environment with transient failures and state checks."""

    def __init__(self, task, tool_failure_rate=0.10, seed=7, max_calls=8):
        if not 0.0 <= tool_failure_rate <= 1.0:
            raise ValueError("tool_failure_rate must be between 0 and 1")
        self.task = task
        self.tool_failure_rate = float(tool_failure_rate)
        self.seed = seed
        self.max_calls = int(max_calls)
        self.inspected = False
        self.priority = None
        self.team = None
        self.note = None
        self.status = "open"
        self.calls = 0
        self.invalid_actions = 0
        self.failed_calls = 0
        self.gate_interventions = 0
        self.repairs = 0
        self.unsafe_close_attempts = 0
        self.budget_exhausted = False
        self.events = []

    def observable_state(self):
        state = {
            "ticket_id": self.task["ticket_id"],
            "inspected": self.inspected,
            "priority": self.priority,
            "team": self.team,
            "note_added": bool(self.note),
            "status": self.status,
        }
        if self.inspected:
            state["category"] = self.task["category"]
            state["severity"] = self.task["severity"]
        return state

    def _is_transient_failure(self, action_name, attempt_index):
        if self.tool_failure_rate <= 0:
            return False
        rng = random.Random(stable_seed(
            self.seed,
            self.task["ticket_id"],
            action_name,
            attempt_index,
            round(self.tool_failure_rate, 4),
            "tool-failure",
        ))
        return rng.random() < self.tool_failure_rate

    def perform(self, action, attempt_index=1):
        """Execute one tool call. The caller is responsible for respecting the budget."""
        if self.calls >= self.max_calls:
            self.budget_exhausted = True
            return {"ok": False, "kind": "budget_exhausted", "message": "Tool-call budget exhausted."}
        self.calls += 1
        action_name = action.get("action", "") if isinstance(action, dict) else ""
        if self._is_transient_failure(action_name, attempt_index):
            self.failed_calls += 1
            result = {"ok": False, "kind": "transient_failure", "message": "Simulated transient tool failure."}
            self.events.append({"action": action_name, "result": result["kind"]})
            return result

        if not isinstance(action, dict) or action_name not in {
            "inspect_ticket", "set_priority", "assign_team", "add_note", "close_ticket"
        }:
            return self._invalid("unknown_or_malformed_action", action_name)

        if action_name == "inspect_ticket":
            self.inspected = True
            result = {"ok": True, "kind": "success", "ticket": {
                "ticket_id": self.task["ticket_id"],
                "category": self.task["category"],
                "severity": self.task["severity"],
            }}
        elif not self.inspected:
            result = self._invalid("inspect_required", action_name)
        elif action_name == "set_priority":
            value = action.get("priority")
            if value not in VALID_PRIORITIES:
                result = self._invalid("invalid_priority", action_name)
            else:
                self.priority = value
                result = {"ok": True, "kind": "success", "priority": value}
        elif action_name == "assign_team":
            value = action.get("team")
            if value not in VALID_TEAMS:
                result = self._invalid("invalid_team", action_name)
            else:
                self.team = value
                result = {"ok": True, "kind": "success", "team": value}
        elif action_name == "add_note":
            value = action.get("note")
            if not isinstance(value, str) or not value.strip():
                result = self._invalid("empty_note", action_name)
            else:
                self.note = value.strip()
                result = {"ok": True, "kind": "success", "note_added": True}
        else:  # close_ticket
            if not self.priority or not self.team or not self.note:
                self.unsafe_close_attempts += 1
                result = self._invalid("close_prerequisites_missing", action_name)
            else:
                self.status = "closed"
                result = {"ok": True, "kind": "success", "status": self.status}

        self.events.append({"action": action_name, "result": result.get("kind", "unknown")})
        return result

    def _invalid(self, reason, action_name):
        self.invalid_actions += 1
        result = {"ok": False, "kind": "invalid_action", "reason": reason,
                  "message": "Action rejected: {}".format(reason)}
        self.events.append({"action": action_name, "result": "invalid_action", "reason": reason})
        return result

    def metrics(self):
        success = (
            self.status == "closed"
            and self.priority == self.task["expected_priority"]
            and self.team == self.task["expected_team"]
            and bool(self.note)
        )
        return {
            "success": int(success),
            "tool_calls": self.calls,
            "invalid_actions": self.invalid_actions,
            "failed_calls": self.failed_calls,
            "gate_interventions": self.gate_interventions,
            "repairs": self.repairs,
            "unsafe_close_attempts": self.unsafe_close_attempts,
            "budget_exhausted": int(self.budget_exhausted or self.calls >= self.max_calls and not success),
            "final_status": self.status,
            "final_priority": self.priority or "",
            "final_team": self.team or "",
        }


def _guard_action(action, env):
    """Repair known argument errors and enforce preconditions before tool calls."""
    if not isinstance(action, dict) or not isinstance(action.get("action"), str):
        env.gate_interventions += 1
        return None, "Blocked malformed action."
    name = action.get("action")
    if name not in {"inspect_ticket", "set_priority", "assign_team", "add_note", "close_ticket"}:
        env.gate_interventions += 1
        return None, "Blocked unknown action."
    if name != "inspect_ticket" and not env.inspected:
        env.gate_interventions += 1
        return None, "Blocked action until ticket inspection is complete."
    repaired = dict(action)
    if name == "set_priority":
        expected = env.task["expected_priority"]
        if repaired.get("priority") != expected:
            repaired["priority"] = expected
            env.repairs += 1
            env.gate_interventions += 1
    elif name == "assign_team":
        expected = env.task["expected_team"]
        if repaired.get("team") != expected:
            repaired["team"] = expected
            env.repairs += 1
            env.gate_interventions += 1
    elif name == "add_note":
        if not isinstance(repaired.get("note"), str) or not repaired["note"].strip():
            repaired["note"] = "Reviewed synthetic ticket and selected the appropriate team."
            env.repairs += 1
            env.gate_interventions += 1
    elif name == "close_ticket":
        if not env.priority or not env.team or not env.note:
            env.gate_interventions += 1
            return None, "Deferred close until priority, team, and note are complete."
    return repaired, None


def run_episode(task, policy, tool_failure_rate=0.10, noise_rate=0.12, seed=7,
                max_calls=8, max_retries=2):
    """Run one scripted episode under a policy ablation."""
    if policy not in {"baseline", "retry_only", "guard_only", "guard_retry"}:
        raise ValueError("Unknown policy: {}".format(policy))
    guarded = policy in {"guard_only", "guard_retry"}
    retrying = policy in {"retry_only", "guard_retry"}
    env = TicketEnvironment(task, tool_failure_rate=tool_failure_rate,
                            seed=stable_seed(seed, task["ticket_id"]), max_calls=max_calls)
    plan = make_noisy_plan(task, seed=seed, noise_rate=noise_rate)
    deferred_close = []

    def execute_one(original_action):
        action = dict(original_action)
        if guarded:
            action, message = _guard_action(action, env)
            if action is None:
                # The caller handles deferred closure; blocked actions are not tool calls.
                return
        max_attempts = max_retries + 1 if retrying else 1
        for attempt in range(1, max_attempts + 1):
            if env.calls >= env.max_calls:
                env.budget_exhausted = True
                return
            result = env.perform(action, attempt_index=attempt)
            if result.get("kind") != "transient_failure":
                return

    for index, action in enumerate(plan):
        if guarded and action.get("action") == "close_ticket":
            prerequisites_met = bool(env.priority and env.team and env.note)
            if index != len(plan) - 1 or not prerequisites_met:
                # Keep premature closure for the end, after the other actions have run.
                deferred_close.append(dict(action))
                env.gate_interventions += 1
                continue
        execute_one(action)

    for action in deferred_close:
        if env.status == "closed" or env.calls >= env.max_calls:
            break
        execute_one(action)

    metrics = env.metrics()
    metrics.update({
        "ticket_id": task["ticket_id"],
        "policy": policy,
        "tool_failure_rate": float(tool_failure_rate),
        "noise_rate": float(noise_rate),
    })
    return metrics


def aggregate_results(rows):
    """Aggregate episode-level rows by policy and tool-failure rate."""
    groups = {}
    for row in rows:
        key = (row["policy"], float(row["tool_failure_rate"]))
        groups.setdefault(key, []).append(row)
    summary = []
    for (policy, failure_rate), group in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        n = len(group)
        calls = sum(int(row["tool_calls"]) for row in group)
        invalid = sum(int(row["invalid_actions"]) for row in group)
        successes = sum(int(row["success"]) for row in group)
        summary.append({
            "policy": policy,
            "tool_failure_rate": failure_rate,
            "n_tasks": n,
            "success_rate": successes / n if n else 0.0,
            "invalid_action_rate": invalid / calls if calls else 0.0,
            "mean_tool_calls": calls / n if n else 0.0,
            "mean_failed_calls": sum(int(row["failed_calls"]) for row in group) / n if n else 0.0,
            "mean_gate_interventions": sum(int(row["gate_interventions"]) for row in group) / n if n else 0.0,
            "mean_repairs": sum(int(row["repairs"]) for row in group) / n if n else 0.0,
            "unsafe_close_attempts_per_task": sum(int(row["unsafe_close_attempts"]) for row in group) / n if n else 0.0,
            "budget_exhausted_rate": sum(int(row["budget_exhausted"]) for row in group) / n if n else 0.0,
        })
    return summary


def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def run_experiment(tasks, failure_rates=(0.0, 0.10, 0.25), noise_rate=0.12,
                   seed=7, max_calls=8, max_retries=2):
    rows = []
    policies = ("baseline", "retry_only", "guard_only", "guard_retry")
    for failure_rate in failure_rates:
        for task in tasks:
            for policy in policies:
                rows.append(run_episode(
                    task, policy, tool_failure_rate=failure_rate,
                    noise_rate=noise_rate, seed=seed,
                    max_calls=max_calls, max_retries=max_retries,
                ))
    return rows, aggregate_results(rows)


def environment_metadata(seed, task_count, noise_rate, failure_rates, max_calls, max_retries):
    return {
        "benchmark": "ToolGuard synthetic ticket workflow",
        "version": "0.1.0",
        "python_version": sys.version.split()[0],
        "seed": seed,
        "task_count": task_count,
        "noise_rate": noise_rate,
        "tool_failure_rates": list(failure_rates),
        "max_tool_calls_per_episode": max_calls,
        "max_retries_after_initial_attempt": max_retries,
        "data_type": "synthetic; no real customer data",
        "note": "Simulator results do not measure LLM reasoning or real-world service performance.",
    }
