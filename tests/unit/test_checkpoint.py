"""Real SQLite checkpoint resume with database operations replaced by test doubles."""

import time
from unittest.mock import MagicMock

import pytest
from langgraph.checkpoint.sqlite import SqliteSaver
from optimizer.config import Settings
from optimizer.workflow import Cancelled, Workflow


def test_checkpoint_resumes_failed_stage_without_repeating_validation(tmp_path):
    db, store = MagicMock(), MagicMock()
    store.get.return_value = {"cancel_requested": 0}
    db.inspect.side_effect = [RuntimeError("interrupted inspection"), {}]
    db.timed.return_value = (1.0, {"plan": {"Plan": {"Node Type": "Result"}}})
    workflow = Workflow(db, store, Settings(), MagicMock())
    config = {"configurable": {"thread_id": "checkpoint-resume"}}
    path = str(tmp_path / "checkpoints.sqlite")
    initial = {
        "session_id": "checkpoint-resume",
        "request": {"sql": "SELECT 1", "provider": "deterministic"},
        "started_at": time.time(),
    }
    with SqliteSaver.from_conn_string(path) as saver:
        graph = workflow.compile(saver)
        with pytest.raises(RuntimeError, match="interrupted inspection"):
            graph.invoke(initial, config)
        snapshot = graph.get_state(config)
        assert snapshot.next == ("inspection",)
        assert snapshot.values["fingerprint"]
    # Reopen the file and compile a fresh graph to exercise persisted recovery.
    with SqliteSaver.from_conn_string(path) as saver:
        graph = workflow.compile(saver)
        result = graph.invoke(None, config)
    assert result["report"]["decision"] == "no_accepted_improvement"
    assert result["report"]["recommended_sql"] == "SELECT 1"
    stages = [call.args[1]["stage"] for call in store.event.call_args_list]
    assert stages.count("validation") == 1
    assert stages.count("inspection") == 2


def test_cancelled_checkpoint_cannot_resume_execution(tmp_path):
    db, store = MagicMock(), MagicMock()
    store.get.return_value = {"cancel_requested": 0}
    db.inspect.side_effect = RuntimeError("interrupted inspection")
    workflow = Workflow(db, store, Settings(), MagicMock())
    path = str(tmp_path / "cancelled.sqlite")
    config = {"configurable": {"thread_id": "cancelled"}}
    with SqliteSaver.from_conn_string(path) as saver:
        graph = workflow.compile(saver)
        with pytest.raises(RuntimeError, match="interrupted inspection"):
            graph.invoke(
                {
                    "session_id": "cancelled",
                    "request": {"sql": "SELECT 1", "provider": "deterministic"},
                    "started_at": time.time(),
                },
                config,
            )
    store.get.return_value = {"cancel_requested": 1}
    with SqliteSaver.from_conn_string(path) as saver:
        graph = workflow.compile(saver)
        with pytest.raises(Cancelled):
            graph.invoke(None, config)
    db.inspect.assert_called_once()
    db.timed.assert_not_called()
