"""Bounded exact result comparison, preserving duplicate and type information."""

from typing import Any

from sqlglot import exp

from optimizer.database import Database
from optimizer.models import Validation
from optimizer.results import equal_rows
from optimizer.safety import order_compatible, structure, validate


def fetch(conn: Any, query: str, db: Database) -> tuple[list[Any], list[Any]]:
    rows: list[Any] = []
    size = 0
    # Named cursor bounds memory before the client receives a large result.
    with conn.cursor(name="pgo_equivalence") as cursor:
        cursor.execute(query)
        description = [(c.name, c.type_code) for c in cursor.description]
        while batch := cursor.fetchmany(256):
            rows.extend(batch)
            size += sum(len(repr(row).encode()) for row in batch)
            if len(rows) > db.settings.max_result_rows or size > db.settings.max_result_bytes:
                raise OverflowError("Equivalence result budget exceeded")
    return rows, description


def rebind(query: str, schema: str) -> str:
    tree = validate(query)
    ctes = {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if table.name not in ctes or table.db:
            table.set("db", exp.to_identifier(schema))
    return tree.sql(dialect="postgres")


def verify(db: Database, original: str, candidate: str) -> Validation:
    a, b = structure(original), structure(candidate)
    changes = {key: [a[key], b[key]] for key in a if a[key] != b[key]}
    if not order_compatible(original, candidate):
        return Validation(
            status="inconclusive",
            reason="Ordering or pagination contract unsupported",
            structural_changes=changes,
        )
    ordered = bool(validate(original).args.get("order"))
    datasets: list[str] = []
    try:
        with db.reader() as conn:
            # Both executions and both datasets share one repeatable-read snapshot.
            for schema in ("commerce", "edge_cases", "edge_empty"):
                left, lt = fetch(conn, rebind(original, schema), db)
                right, rt = fetch(conn, rebind(candidate, schema), db)
                if lt != rt or not equal_rows(left, right, ordered):
                    return Validation(
                        status="failed",
                        reason=f"Values, types, columns or multiplicities differ on {schema}",
                        datasets=datasets + [schema],
                        structural_changes=changes,
                    )
                datasets.append(schema)
    except OverflowError as exc:
        return Validation(
            status="inconclusive", reason=str(exc), datasets=datasets, structural_changes=changes
        )
    return Validation(
        status="differentially_validated",
        reason="Exact finite snapshot comparisons passed, no formal proof",
        datasets=datasets,
        structural_changes=changes,
    )
