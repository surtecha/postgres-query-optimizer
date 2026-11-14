"""Execution cost gates with recorded PostgreSQL responses, without a server."""

from unittest.mock import MagicMock

import pytest
from optimizer.config import Settings
from optimizer.database import BudgetExceeded, Database


@pytest.mark.parametrize("entrypoint", ["analyzed_plan", "timed"])
def test_over_budget_estimate_prevents_execution(entrypoint):
    database = Database(Settings(max_plan_cost=10))
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = ([{"Plan": {"Total Cost": 11}}],)
    try:
        with pytest.raises(BudgetExceeded):
            if entrypoint == "analyzed_plan":
                database.plan(conn, "SELECT 1", analyze=True)
            else:
                database.timed(conn, "SELECT 1")
        conn.execute.assert_called_once_with("EXPLAIN (FORMAT JSON) SELECT 1")
    finally:
        database.close()


def test_allowed_query_records_server_latency_after_preflight():
    database = Database(Settings(max_plan_cost=10))
    conn = MagicMock()
    conn.execute.return_value.fetchone.side_effect = [
        ([{"Plan": {"Total Cost": 1}}],),
        ([{"Plan": {"Total Cost": 1}, "Execution Time": 2.5}],),
    ]
    try:
        latency, detail = database.timed(conn, "SELECT 1")
        assert latency == 2.5
        assert detail["wall_ms"] >= 0
        assert [call.args[0] for call in conn.execute.call_args_list] == [
            "EXPLAIN (FORMAT JSON) SELECT 1",
            "EXPLAIN (ANALYZE, BUFFERS, TIMING, FORMAT JSON) SELECT 1",
        ]
    finally:
        database.close()
