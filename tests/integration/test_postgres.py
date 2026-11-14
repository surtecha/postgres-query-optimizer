"""Real PostgreSQL checks. Run only against the explicitly managed local stack."""
import os
import time

import pytest
from fastapi.testclient import TestClient

from optimizer.api import create_app
from optimizer.config import Settings
from optimizer.database import Database
from optimizer.equivalence import verify
from optimizer.models import IndexProposal
from optimizer.persistence import Store
from optimizer.safety import UnsafeSQL
from optimizer.workloads import WORKLOADS

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.environ.get("PGO_INTEGRATION") != "1", reason="Requires explicit controlled PostgreSQL stack")]


@pytest.fixture
def db():
    database = Database(Settings())
    database.open()
    yield database
    database.close()


def test_real_metadata_and_plans(db):
    for workload in WORKLOADS:
        metadata = db.inspect(workload["sql"])
        assert metadata["dataset"][1] >= 10000
        with db.reader() as conn:
            plan = db.plan(conn, workload["sql"], analyze=True)
        assert plan["Execution Time"] >= 0
        assert "Node Type" in plan["Plan"]


def test_reader_is_read_only(db):
    with pytest.raises(Exception, match="read-only"):
        with db.reader() as conn:
            conn.execute("DELETE FROM commerce.orders")


def test_equivalence_preserves_bags_and_nulls(db):
    a = "SELECT region FROM commerce.customers"
    assert verify(db, a, a).status == "differentially_validated"
    assert verify(db, a, "SELECT region FROM commerce.customers WHERE region IS NOT NULL").status == "failed"


def test_result_limit_is_inconclusive(db):
    db.settings.max_result_rows = 1
    assert verify(db, "SELECT id FROM commerce.orders", "SELECT id FROM commerce.orders").status == "inconclusive"


def test_managed_index_cleanup(db):
    with db.experiment_lock() as admin:
        name="pgo_exp_integration"
        ddl=db.index_ddl(admin,IndexProposal(table="orders",columns=["customer_id"]),name)
        try:
            admin.execute(ddl)
            assert admin.execute("SELECT to_regclass(%s)",("commerce."+name,)).fetchone()[0]
        finally:
            db.drop_index(admin,name)
        assert admin.execute("SELECT to_regclass(%s)",("commerce."+name,)).fetchone()[0] is None


def test_index_column_injection_rejected(db):
    with db.experiment_lock() as admin, pytest.raises(UnsafeSQL):
        db.index_ddl(admin,IndexProposal(table="orders",columns=["id); DROP TABLE orders;--"]),"pgo_exp_injection")


def test_api_session_is_persisted_and_idempotent():
    config = Settings()
    app=create_app(config)
    with TestClient(app) as client:
        body={"sql":"SELECT id FROM commerce.orders WHERE id=1"}
        first=client.post("/api/v1/optimizations",json=body,headers={"Idempotency-Key":"integration-idempotency"})
        second=client.post("/api/v1/optimizations",json=body,headers={"Idempotency-Key":"integration-idempotency"})
        assert first.status_code==202
        assert first.json()["id"]==second.json()["id"]
        persisted=Store(config.app_dsn.get_secret_value()).get(first.json()["id"])
        assert persisted["request"]["sql"]==body["sql"]
        assert client.post("/api/v1/optimizations",json={"sql":"DELETE FROM commerce.orders"}).status_code==422
        assert client.get("/api/v1/summary").json()["total"] >= 1
        assert client.post("/api/v1/optimizations",content=b'x'*25000).status_code==413


def test_complete_durable_session_with_worker():
    with TestClient(create_app()) as client:
        result=client.post("/api/v1/optimizations",json={"sql":"SELECT id FROM commerce.orders WHERE id=1"})
        assert result.status_code==202
        identifier=result.json()["id"]
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            row=client.get(f"/api/v1/optimizations/{identifier}").json()
            if row["status"] not in ("queued","running"):
                break
            time.sleep(.2)
        assert row["status"]=="completed", row
        report=row["report"]
        assert report["decision"]=="no_accepted_improvement"
        assert report["baseline_plan"]["Plan"]["Node Type"]
        assert report["recommended_sql"]==report["original_sql"]
