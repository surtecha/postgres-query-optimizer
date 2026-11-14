"""Process interruption checks; require the normal Compose worker to be stopped."""

import os
import subprocess
import sys
import time
import uuid

import psycopg
import pytest
from optimizer.config import Settings
from optimizer.persistence import Store

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("PGO_INTEGRATION") != "1" or os.environ.get("PGO_RECOVERY") != "1",
        reason="Requires controlled PostgreSQL and an explicitly stopped Compose worker",
    ),
]

INTERRUPTED_WORKER = """
import os
import time
from pathlib import Path
from optimizer.models import IndexProposal
from optimizer.worker import run
from optimizer.workflow import Workflow

def inspection(self, state):
    ddl = self.db.index_ddl(
        self.admin, IndexProposal(table="orders", columns=["customer_id"]),
        os.environ["RECOVERY_INDEX"],
    )
    self.admin.execute(ddl)
    Path(os.environ["RECOVERY_MARKER"]).write_text(state["session_id"])
    while True:
        time.sleep(0.1)

Workflow.inspection = inspection
run()
"""


def wait_until(predicate, process, log, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        assert process.poll() is None, log.read_text()
        time.sleep(0.05)
    pytest.fail(f"Worker progress timed out: {log.read_text()}")


@pytest.mark.parametrize("cancelled", [False, True], ids=["resume", "cancel"])
def test_killed_worker_recovers_checkpoint_and_cleans_index(tmp_path, cancelled):
    settings = Settings()
    store = Store(settings.app_dsn.get_secret_value())
    assert not store.list(status="queued", limit=1), "Recovery tests require an empty queue"
    assert not store.list(status="running", limit=1), "Stop the worker and drain active sessions"
    marker = tmp_path / "inspection-started"
    log = tmp_path / "worker.log"
    index_name = "pgo_exp_" + uuid.uuid4().hex[:24]
    environment = {
        **os.environ,
        "PGO_STATE_DIR": str(tmp_path / "state"),
        "RECOVERY_MARKER": str(marker),
        "RECOVERY_INDEX": index_name,
    }
    identifier = store.create(
        {"sql": "SELECT id FROM commerce.orders WHERE id=1", "provider": "deterministic"},
        None,
        settings.max_pending,
    )
    process = None
    try:
        with log.open("w") as output:
            process = subprocess.Popen(
                [sys.executable, "-c", INTERRUPTED_WORKER],
                env=environment,
                stdout=output,
                stderr=subprocess.STDOUT,
            )
            wait_until(marker.exists, process, log)
            assert marker.read_text() == identifier
            row = store.get(identifier)
            assert row["status"] == "running"
            assert row["attempts"] == 1
            if cancelled:
                assert store.cancel(identifier)
            # SIGKILL bypasses Python finally blocks and leaves the committed index behind.
            process.kill()
            process.wait(timeout=10)
            with psycopg.connect(settings.admin_dsn.get_secret_value()) as admin:
                assert (
                    admin.execute("SELECT to_regclass(%s)", ("commerce." + index_name,)).fetchone()[
                        0
                    ]
                    is not None
                )
            # Recovery must use the same real SQLite file and PostgreSQL queue row.
            process = subprocess.Popen(
                [sys.executable, "-m", "optimizer.worker"],
                env=environment,
                stdout=output,
                stderr=subprocess.STDOUT,
            )

            def terminal():
                current = store.get(identifier)
                return current if current["status"] not in ("queued", "running") else None

            row = wait_until(terminal, process, log)
            assert row["status"] == ("cancelled" if cancelled else "completed"), row
            assert row["attempts"] == 2
            assert sum(event["stage"] == "validation" for event in row["events"]) == 1
            if not cancelled:
                assert row["report"]["recommended_sql"] == row["request"]["sql"]
        with psycopg.connect(settings.admin_dsn.get_secret_value()) as admin:
            # Observe cleanup without triggering the cleanup mechanism in this connection.
            assert (
                admin.execute("SELECT to_regclass(%s)", ("commerce." + index_name,)).fetchone()[0]
                is None
            )
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        store.cancel(identifier)
        store.engine.dispose()
