import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from memtrust import generate_scenarios, evaluate_scenario, run_experiment, summarize, summarize_by_seed

class MemTrustTests(unittest.TestCase):
    def test_generation_is_deterministic(self):
        self.assertEqual(generate_scenarios(), generate_scenarios())

    def test_scenario_count_and_unique_ids(self):
        scenarios = generate_scenarios()
        self.assertEqual(len(scenarios), 3 * 3 * 250)
        self.assertEqual(len({s['scenario_id'] for s in scenarios}), len(scenarios))

    def test_policies_are_known_and_results_bounded(self):
        scenario = next(s for s in generate_scenarios() if s['poison_present'] == 1)
        for policy in ('baseline_relevance', 'provenance_filter', 'provenance_plus_corroboration'):
            result = evaluate_scenario(scenario, policy)
            self.assertIn(result['task_success'], (0, 1))
            self.assertIn(result['attack_success'], (0, 1))
            self.assertIn(result['abstained'], (0, 1))

    def test_corroboration_blocks_injected_memory(self):
        for scenario in generate_scenarios():
            if scenario['poison_present']:
                result = evaluate_scenario(scenario, 'provenance_plus_corroboration')
                self.assertEqual(result['attack_success'], 0)

    def test_summary_has_all_policy_rate_combinations(self):
        summaries = summarize(run_experiment(generate_scenarios()))
        self.assertEqual(len(summaries), 9)
        self.assertTrue(all('attack_success_rate_on_poisoned' in s for s in summaries))
        self.assertEqual(len(summarize_by_seed(run_experiment(generate_scenarios()))), 27)

if __name__ == '__main__':
    unittest.main()
