import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("analyze_budget_efficiency.py")
SPEC = importlib.util.spec_from_file_location("rq4_analyzer", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def attempt(number, tokens=10, gate_ms=100):
    return {
        "number": number,
        "usage": {
            "prompt_tokens": tokens - 2,
            "completion_tokens": 2,
            "total_tokens": tokens,
            "prompt_cache_hit_tokens": 3,
            "prompt_cache_miss_tokens": tokens - 5,
        },
        "gates": [{"name": "compiler", "duration_ms": gate_ms}],
    }


class BudgetEfficiencyTests(unittest.TestCase):
    def test_prefix_stops_at_available_attempts(self):
        task = {
            "result": {
                "status": "verified_success",
                "candidates_used": 2,
                "sealed_attempts": [
                    {"attempt": 2, "result": {"status": "pass", "duration_ms": 50}}
                ],
            },
            "attempts": [attempt(1), attempt(2)],
        }
        first = MODULE.task_prefix(task, 1)
        third = MODULE.task_prefix(task, 3)
        self.assertFalse(first["success"])
        self.assertTrue(third["success"])
        self.assertEqual(first["candidate_count"], 1)
        self.assertEqual(third["candidate_count"], 2)
        self.assertEqual(third["stage_ms"]["openplc_sealed"], 50)

    def test_infrastructure_is_visible_only_after_terminal_attempt(self):
        task = {
            "result": {
                "status": "infrastructure_error",
                "candidates_used": 3,
                "sealed_attempts": [],
            },
            "attempts": [attempt(1), attempt(2), attempt(3)],
        }
        self.assertFalse(MODULE.task_prefix(task, 1)["infrastructure"])
        self.assertTrue(MODULE.task_prefix(task, 3)["infrastructure"])

    def test_marginal_costs_are_successive_differences(self):
        rows = [
            {"budget": 1, "success_count": 2, "candidate_count": 4,
             "total_tokens": 40, "estimated_api_cost_usd": 0.1,
             "validator_work_seconds": 5.0},
            {"budget": 3, "success_count": 3, "candidate_count": 7,
             "total_tokens": 70, "estimated_api_cost_usd": 0.2,
             "validator_work_seconds": 8.0},
        ]
        MODULE.add_marginal_costs(rows)
        self.assertEqual(rows[1]["added_successes"], 1)
        self.assertEqual(rows[1]["added_candidates"], 3)
        self.assertEqual(rows[1]["marginal_tokens_per_added_success"], 30)

    def test_sealed_limit_uses_first_n_queries(self):
        task = {
            "result": {
                "sealed_attempts": [
                    {"attempt": 2, "result": {"status": "fail"}},
                    {"attempt": 4, "result": {"status": "pass"}},
                ]
            },
            "attempts": [attempt(i) for i in range(1, 5)],
        }
        rows = MODULE.sealed_sensitivity([task])
        self.assertEqual(rows[0]["success_count"], 0)
        self.assertEqual(rows[0]["candidate_count"], 2)
        self.assertEqual(rows[1]["success_count"], 1)

    def test_bootstrap_intervals_are_task_level_and_deterministic(self):
        tasks = []
        for winning_attempt in (1, 2, None, None):
            sealed = [] if winning_attempt is None else [
                {"attempt": winning_attempt, "result": {"status": "pass", "duration_ms": 1}}
            ]
            tasks.append({
                "result": {
                    "status": "verified_success" if sealed else "candidate_budget_exhausted",
                    "candidates_used": 2,
                    "sealed_attempts": sealed,
                },
                "attempts": [attempt(1), attempt(2)],
            })
        prices = {
            "input_cache_hit_per_million": 0.1,
            "input_cache_miss_per_million": 0.2,
            "output_per_million": 0.3,
        }
        rows = [MODULE.aggregate_budget(tasks, k, prices) for k in (1, 2)]
        MODULE.add_marginal_costs(rows)
        MODULE.add_bootstrap_intervals(rows, tasks, prices, samples=100, seed=7)
        self.assertIn("success_rate_ci95", rows[0])
        self.assertEqual(len(rows[1]["tokens_per_success_ci95"]), 2)
        self.assertLessEqual(rows[0]["success_rate_ci95"][0], 0.25)
        self.assertGreaterEqual(rows[1]["success_rate_ci95"][1], 0.5)

    def test_restart_limit_counts_only_observed_recoveries(self):
        tasks = [
            {
                "result": {"success": True},
                "ledger": [{"event_type": "inconclusive_blind_restart_scheduled"}],
            },
            {"result": {"success": True}, "ledger": []},
            {"result": {"success": False}, "ledger": []},
        ]
        rows = MODULE.inconclusive_sensitivity(tasks)
        self.assertEqual(rows[0]["success_count"], 1)
        self.assertEqual(rows[1]["success_count"], 2)


if __name__ == "__main__":
    unittest.main()
