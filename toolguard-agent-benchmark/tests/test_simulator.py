import tempfile
import unittest
from pathlib import Path

from toolguard.simulator import (
    TicketEnvironment,
    _guard_action,
    generate_tasks,
    make_noisy_plan,
    run_episode,
)


class ToolGuardTests(unittest.TestCase):
    def setUp(self):
        self.task = generate_tasks(1, seed=7)[0]

    def test_dataset_generation_is_reproducible(self):
        self.assertEqual(generate_tasks(8, seed=11), generate_tasks(8, seed=11))

    def test_dataset_writes_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tasks.csv"
            generated = generate_tasks(5, seed=3, output_path=path)
            self.assertEqual(len(generated), 5)
            self.assertTrue(path.exists())
            self.assertIn("ticket_id", path.read_text(encoding="utf-8"))

    def test_close_before_prerequisites_is_rejected(self):
        env = TicketEnvironment(self.task, tool_failure_rate=0.0, seed=7)
        env.perform({"action": "inspect_ticket"})
        result = env.perform({"action": "close_ticket"})
        self.assertEqual(result["kind"], "invalid_action")
        self.assertEqual(env.unsafe_close_attempts, 1)

    def test_guard_repairs_wrong_priority(self):
        env = TicketEnvironment(self.task, tool_failure_rate=0.0, seed=7)
        env.perform({"action": "inspect_ticket"})
        wrong = "urgent" if self.task["expected_priority"] != "urgent" else "low"
        action, message = _guard_action({"action": "set_priority", "priority": wrong}, env)
        self.assertIsNone(message)
        self.assertEqual(action["priority"], self.task["expected_priority"])
        self.assertEqual(env.repairs, 1)

    def test_guarded_retry_policy_completes_clean_task_without_failures(self):
        task = generate_tasks(1, seed=19)[0]
        result = run_episode(task, "guard_retry", tool_failure_rate=0.0,
                             noise_rate=0.0, seed=19, max_calls=8)
        self.assertEqual(result["success"], 1)
        self.assertEqual(result["invalid_actions"], 0)

    def test_baseline_is_reproducible(self):
        task = generate_tasks(1, seed=27)[0]
        a = run_episode(task, "baseline", tool_failure_rate=0.10,
                        noise_rate=0.20, seed=27)
        b = run_episode(task, "baseline", tool_failure_rate=0.10,
                        noise_rate=0.20, seed=27)
        self.assertEqual(a, b)

    def test_plan_has_five_actions(self):
        self.assertEqual(len(make_noisy_plan(self.task, seed=7, noise_rate=0.0)), 5)


if __name__ == "__main__":
    unittest.main()
