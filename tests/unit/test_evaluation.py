import unittest

from optimizer.evaluation_metrics import aggregate


class EvaluationTests(unittest.TestCase):
    def test_missing_arm_not_a_success(self):
        result = aggregate([{"provider": "openai", "status": "not_run"}])["openai"]
        self.assertEqual(result["executed_workloads"], 0)
        self.assertIsNone(result["valid_candidate_rate"])
        self.assertIsNone(result["tokens"])

    def test_measured_rates(self):
        rows = [
            {
                "provider": "deterministic",
                "session": {
                    "status": "completed",
                    "report": {
                        "decision": "validated_improvement",
                        "duration_seconds": 2,
                        "model_usage": {"calls": 0, "tokens": 0, "estimated_cost_usd": 0},
                        "candidates": [
                            {
                                "safety": {"passed": True},
                                "validation": {"status": "differentially_validated"},
                                "accepted": True,
                                "benchmark": {"median_speedup": 2, "runs": [{"latency_ms": 5}]},
                            },
                            {"safety": {"passed": False}, "accepted": False},
                        ],
                    },
                },
            }
        ]
        result = aggregate(rows)["deterministic"]
        self.assertEqual(result["valid_candidate_rate"], 0.5)
        self.assertEqual(result["candidate_acceptance_rate"], 0.5)
        self.assertEqual(result["median_accepted_speedup"], 2)
        self.assertEqual(result["database_execution_ms"], 5)

    def test_failure_not_counted_as_completed(self):
        result = aggregate([{"provider": "deterministic", "session": {"status": "failed"}}])[
            "deterministic"
        ]
        self.assertEqual(result["completed_workloads"], 0)
        self.assertIsNone(result["workloads_improved_rate"])


def test_failed_model_arm_is_separated_from_fallback_improvements():
    rows = [
        {
            "provider": "openai",
            "session": {
                "status": "completed",
                "report": {
                    "decision": "validated_improvement",
                    "model_usage": {
                        "provider": "openai",
                        "calls": 1,
                        "tokens": 123,
                        "error": "ValidationError",
                        "estimated_cost_usd": None,
                    },
                    "candidates": [
                        {
                            "source": "deterministic",
                            "accepted": True,
                            "benchmark": {"median_speedup": 2, "runs": []},
                        }
                    ],
                },
            },
        }
    ]
    result = aggregate(rows)["openai"]
    assert result["completed_workloads"] == 1
    assert result["evaluated_workloads"] == 0
    assert result["fallback_only_workloads"] == 1
    assert result["workloads_improved_rate"] is None
    assert result["median_accepted_speedup"] is None
    assert result["tokens"] == 123


def test_no_model_call_is_not_model_assisted_evidence():
    rows = [
        {
            "provider": "openai",
            "session": {
                "status": "completed",
                "report": {
                    "decision": "no_accepted_improvement",
                    "model_usage": {"provider": "openai", "calls": 0, "tokens": 0},
                    "candidates": [],
                },
            },
        }
    ]
    result = aggregate(rows)["openai"]
    assert result["evaluated_workloads"] == 0
    assert result["fallback_only_workloads"] == 1


def test_valid_model_run_reports_model_candidate_contribution():
    rows = [
        {
            "provider": "openai",
            "session": {
                "status": "completed",
                "report": {
                    "decision": "validated_improvement",
                    "model_usage": {"provider": "openai", "calls": 1, "tokens": 20},
                    "candidates": [
                        {
                            "source": "openai",
                            "accepted": True,
                            "benchmark": {"median_speedup": 1.5, "runs": []},
                        }
                    ],
                },
            },
        }
    ]
    result = aggregate(rows)["openai"]
    assert result["evaluated_workloads"] == 1
    assert result["fallback_only_workloads"] == 0
    assert result["model_candidates"] == 1
    assert result["accepted_model_candidates"] == 1
    assert result["workloads_improved_rate"] == 1
