"""Aggregate measured evidence without treating missing model arms as successes."""
import statistics
from typing import Any


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for provider in ("deterministic", "openai"):
        selected = [r for r in rows if r["provider"] == provider]
        executed = [r for r in selected if r.get("session")]
        completed = [r for r in executed if r["session"].get("status") == "completed"]
        reports = [r["session"].get("report") or {} for r in completed]
        candidates = [c for report in reports for c in report.get("candidates", [])]
        valid = [c for c in candidates if c.get("safety", {}).get("passed")]
        equivalent = [c for c in candidates if c.get("validation", {}).get("status") == "differentially_validated"]
        accepted = [c for c in candidates if c.get("accepted")]
        speedups = [c["benchmark"]["median_speedup"] for c in accepted]
        usage = [r.get("model_usage", {}) for r in reports]
        measured = [c for c in candidates if "benchmark" in c]
        def rate(numerator: int, denominator: int) -> float | None:
            return numerator / denominator if denominator else None
        result[provider] = {
            "requested_workloads": len(selected), "executed_workloads": len(executed),
            "completed_workloads": len(completed), "not_run": len(selected)-len(executed),
            "valid_candidate_rate": rate(len(valid), len(candidates)),
            "equivalence_pass_rate": rate(len(equivalent), len(valid)),
            "candidate_acceptance_rate": rate(len(accepted), len(candidates)),
            "workloads_improved_rate": rate(sum(r.get("decision") == "validated_improvement" for r in reports), len(completed)),
            "accepted_workloads_regressed_rate": rate(sum(any(c.get("accepted") and c["benchmark"]["median_speedup"] < 1 for c in r.get("candidates", [])) for r in reports), len(completed)),
            "experimental_candidate_regression_rate": rate(sum(c["benchmark"]["median_speedup"] < 1 for c in measured), len(measured)),
            "median_accepted_speedup": statistics.median(speedups) if speedups else None,
            "total_optimization_seconds": sum(r.get("duration_seconds", 0) for r in reports),
            "model_calls": sum(u.get("calls", 0) for u in usage),
            "tokens": sum(u.get("tokens", 0) for u in usage) if usage and all(isinstance(u.get("tokens"), int) for u in usage) else None,
            "estimated_model_cost_usd": sum(u["estimated_cost_usd"] for u in usage) if usage and all(u.get("estimated_cost_usd") is not None for u in usage) else None,
            "cost_per_success_usd": None,
            "database_execution_ms": sum(sum(run["latency_ms"] for run in c["benchmark"].get("runs", [])) for c in measured),
            "limitations": ["Metrics cover completed reports only", "Database time excludes setup and correctness reads",
                            "Cost per success is unavailable without verified provider pricing"]}
    return result
