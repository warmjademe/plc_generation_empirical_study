import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("summarize_rq2.py")
SPEC = importlib.util.spec_from_file_location("rq2_summary", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def summary(arm, success_ids=()):
    runs = [
        {
            "task_id": f"C{index // 10 + 1:02d}_T{index:03d}",
            "success": index in success_ids,
            "status": "verified_success" if index in success_ids else "candidate_budget_exhausted",
        }
        for index in range(100)
    ]
    document = {
        "task_count": 100,
        "method": "evidence" if arm != "M01" else "raw_repair",
        "requested_model": "deepseek-v4-flash",
        "dataset_manifest_sha256": "dataset",
        "success_count": len(set(success_ids)),
        "status_counts": {},
        "runs": runs,
        "all_ledgers_valid": True,
        "all_model_identities_valid": True,
        "sealed_judge_count_valid": True,
        "inconclusive_restart_count_valid": True,
    }
    if arm == "M01":
        document.update({
            "ablation_id": "M01_without_component_1",
            "core_component_1_enabled": False,
            "core_component_2_enabled": True,
        })
    elif arm == "M10":
        document.update({
            "ablation_id": "M10_without_component_2",
            "core_component_1_enabled": True,
            "core_component_2_enabled": False,
        })
    return document


class RQ2SummaryTests(unittest.TestCase):
    def test_exact_mcnemar(self):
        self.assertEqual(MODULE.exact_mcnemar(0, 0), 1.0)
        self.assertAlmostEqual(MODULE.exact_mcnemar(5, 0), 0.0625)
        self.assertEqual(MODULE.exact_mcnemar(2, 2), 1.0)

    def test_paired_risk_difference(self):
        full = {"a": {"success": True}, "b": {"success": False}}
        ablated = {"a": {"success": False}, "b": {"success": False}}
        self.assertEqual(MODULE.paired_risk_difference(full, ablated, ["a", "b"]), 0.5)

    def test_bh_adjustment_is_monotonic_in_rank(self):
        rows = [{"p_exact": 0.01}, {"p_exact": 0.04}]
        MODULE.bh_adjust(rows)
        self.assertEqual(rows[0]["p_bh"], 0.02)
        self.assertEqual(rows[1]["p_bh"], 0.04)

    def test_validate_accepts_only_two_named_deletions(self):
        ids = MODULE.validate(summary("full", {1, 2}), summary("M01", {1}), summary("M10", {2}))
        self.assertEqual(len(ids), 100)

    def test_validate_rejects_audit_failure(self):
        m10 = summary("M10", {2})
        m10["all_ledgers_valid"] = False
        with self.assertRaisesRegex(ValueError, "protocol audit"):
            MODULE.validate(summary("full", {1, 2}), summary("M01", {1}), m10)


if __name__ == "__main__":
    unittest.main()
