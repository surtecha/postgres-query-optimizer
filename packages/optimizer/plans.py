"""Pure JSON plan diagnostics. Parent times and buffers are inclusive."""
from typing import Any

FIELDS = ("Node Type", "Total Cost", "Startup Cost", "Plan Rows", "Actual Rows",
          "Actual Total Time", "Actual Loops", "Shared Hit Blocks", "Shared Read Blocks",
          "Temp Read Blocks", "Temp Written Blocks", "Sort Method", "Sort Space Used",
          "Sort Space Type", "Join Type", "Index Name", "Filter", "Rows Removed by Filter",
          "Rows Removed by Join Filter", "Relation Name", "Alias", "Parent Relationship")


def flatten(plan: dict[str, Any]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []

    def visit(node: dict[str, Any], path: str) -> None:
        nodes.append({"path": path, **{field: node.get(field) for field in FIELDS}})
        for i, child in enumerate(node.get("Plans", [])):
            visit(child, f"{path}.{i}")
    visit(plan.get("Plan", plan), "0")
    return nodes


def diagnose(plan: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for n in flatten(plan):
        rows = n.get("Actual Rows")
        estimate = n.get("Plan Rows") or 0
        loops = n.get("Actual Loops") or 1
        removed = n.get("Rows Removed by Filter") or 0
        elapsed = (n.get("Actual Total Time") or 0) * loops
        kind = n["Node Type"] or ""
        flags: list[tuple[str, str]] = []
        if rows is not None and max(rows, estimate) >= 100 and (max(rows, estimate) + 1) / (min(rows, estimate) + 1) >= 10:
            flags.append(("cardinality", "Check statistics freshness and correlated predicates"))
        if kind == "Seq Scan" and rows is not None and rows + removed >= 10000 and removed / max(1, rows + removed) > 0.9:
            flags.append(("selective_scan", "Large selective scan may benefit from a predicate index"))
        if kind == "Nested Loop" and elapsed > 20:
            flags.append(("nested_loop", "Inspect inner scans and join cardinalities"))
        if n.get("Sort Space Type") == "Disk" or (n.get("Temp Written Blocks") or 0) > 0:
            flags.append(("spill", "Temporary storage used, inspect row width and sort volume"))
        if "Sort" in kind and (estimate > 10000 or elapsed > 20):
            flags.append(("large_sort", "Inspect ordering and index compatibility"))
        if "Aggregate" in kind and elapsed > 20:
            flags.append(("aggregation", "Aggregation has material inclusive execution time"))
        if n.get("Parent Relationship") == "SubPlan" and loops > 100:
            flags.append(("repeated_subplan", "Correlated subplan executes repeatedly"))
        if (n.get("Shared Read Blocks") or 0) > 1000:
            flags.append(("buffer_reads", "High physical buffer reads, compare warm-cache trials"))
        if removed > 10000 and removed > (rows or estimate) * 10:
            flags.append(("filter_rejection", "Most scanned rows are discarded by the filter"))
        for code, message in flags:
            diagnostics.append({"code": code, "path": n["path"], "message": message,
                                "evidence": n, "inclusive_time_ms": elapsed})
    return diagnostics


def compare_plans(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    a, b = flatten(baseline), flatten(candidate)
    def signature(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{key: n.get(key) for key in ("Node Type", "Relation Name", "Join Type", "Index Name",
                 "Plan Rows", "Sort Method", "Sort Space Type")} for n in nodes]
    def root_metric(plan: dict[str, Any], key: str) -> float:
        return float(plan.get("Plan", plan).get(key, 0))
    return {"baseline_operators": signature(a), "candidate_operators": signature(b),
            "execution_ms_delta": candidate.get("Execution Time", 0) - baseline.get("Execution Time", 0),
            "shared_hits_delta": root_metric(candidate, "Shared Hit Blocks") - root_metric(baseline, "Shared Hit Blocks"),
            "shared_reads_delta": root_metric(candidate, "Shared Read Blocks") - root_metric(baseline, "Shared Read Blocks")}
