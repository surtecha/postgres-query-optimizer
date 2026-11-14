import os
import signal
import time
from typing import Any

import psycopg
from langgraph.checkpoint.sqlite import SqliteSaver
from prometheus_client import start_http_server

from optimizer.config import Settings
from optimizer.database import BudgetExceeded, Database
from optimizer.persistence import Store
from optimizer.telemetry import setup
from optimizer.workflow import Cancelled, Workflow


def run() -> None:
    settings = Settings()
    settings.state_dir.mkdir(parents=True, exist_ok=True)
    os.environ["LANGGRAPH_STRICT_MSGPACK"] = "true"
    setup(settings.otlp_endpoint)
    start_http_server(9101)
    store = Store(settings.app_dsn.get_secret_value())
    db = Database(settings)
    db.open()
    stopping = False

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    # Single active benchmark worker. Connection loss releases the lock.
    with psycopg.connect(
        settings.app_dsn.get_secret_value().replace("postgresql+psycopg:", "postgresql:"),
        autocommit=True,
    ) as leader:
        lock = leader.execute("SELECT pg_try_advisory_lock(718029413)").fetchone()
        if lock is None or not lock[0]:
            raise RuntimeError("Another worker is active")
        store.recover()
        try:
            while not stopping:
                row = store.claim()
                if row is None:
                    time.sleep(0.5)
                    continue
                identifier = row["id"]
                try:
                    with (
                        db.experiment_lock() as admin,
                        SqliteSaver.from_conn_string(
                            str(settings.state_dir / "checkpoints.sqlite")
                        ) as saver,
                    ):
                        graph = Workflow(db, store, settings, admin).compile(saver)
                        config = {"configurable": {"thread_id": identifier}, "recursion_limit": 32}
                        snapshot = graph.get_state(config)
                        initial = {
                            "session_id": identifier,
                            "request": row["request"],
                            "started_at": time.time(),
                        }
                        state = graph.invoke(None if snapshot.values else initial, config)
                        store.finish(identifier, "completed", state["report"])
                except Cancelled:
                    store.finish(identifier, "cancelled", {"error": "Cancellation requested"})
                except BudgetExceeded as exc:
                    store.finish(identifier, "budget_exceeded", {"error": str(exc)})
                except Exception as exc:
                    store.event(
                        identifier,
                        {"stage": "worker", "status": "error", "category": type(exc).__name__},
                    )
                    store.finish(identifier, "failed", {"error": type(exc).__name__})
        finally:
            db.close()
            store.engine.dispose()


if __name__ == "__main__":
    run()
