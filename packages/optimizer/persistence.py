"""PostgreSQL-backed durable queue and JSON reports. Schema managed by Alembic."""

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    func,
    select,
    text,
    update,
)
from sqlalchemy.engine import Engine

metadata = MetaData()
sessions = Table(
    "optimization_sessions",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("status", String(24), nullable=False),
    Column("request", JSON, nullable=False),
    Column("report", JSON, nullable=True),
    Column("events", JSON, nullable=False),
    Column("cancel_requested", Integer, nullable=False, default=0),
    Column("attempts", Integer, nullable=False, default=0),
    Column("idempotency_key", String(128), unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


class QueueFull(ValueError):
    pass


class Store:
    def __init__(self, dsn: str) -> None:
        self.engine: Engine = create_engine(dsn, pool_size=3, max_overflow=0, pool_pre_ping=True)

    def create(self, request: dict[str, Any], key: str | None, maximum: int) -> str:
        with self.engine.begin() as conn:
            # Serialize quota check and enqueue across concurrent HTTP requests.
            conn.exec_driver_sql("SELECT pg_advisory_xact_lock(718029412)")
            if key:
                row = conn.execute(
                    select(sessions.c.id, sessions.c.request).where(
                        sessions.c.idempotency_key == key
                    )
                ).first()
                if row:
                    if row.request != request:
                        raise ValueError("Idempotency key already used for another request")
                    return str(row.id)
            pending = conn.execute(
                select(func.count())
                .select_from(sessions)
                .where(sessions.c.status.in_(["queued", "running"]))
            ).scalar_one()
            if pending >= maximum:
                raise QueueFull("Execution queue is full")
            identifier = str(uuid.uuid4())
            now = dt.datetime.now(dt.UTC)
            conn.execute(
                sessions.insert().values(
                    id=identifier,
                    request=request,
                    status="queued",
                    events=[],
                    attempts=0,
                    cancel_requested=0,
                    idempotency_key=key,
                    created_at=now,
                    updated_at=now,
                )
            )
            return identifier

    def get(self, identifier: str) -> dict[str, Any] | None:
        with self.engine.connect() as conn:
            row = (
                conn.execute(select(sessions).where(sessions.c.id == identifier)).mappings().first()
            )
            return dict(row) if row else None

    def list(
        self, offset: int = 0, limit: int = 25, status: str | None = None
    ) -> list[dict[str, Any]]:
        query = select(sessions).order_by(sessions.c.created_at.desc()).offset(offset).limit(limit)
        if status:
            query = query.where(sessions.c.status == status)
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(query).mappings()]

    def recover(self) -> None:
        # Called only under the worker's exclusive PostgreSQL advisory lock.
        with self.engine.begin() as conn:
            conn.execute(
                update(sessions).where(sessions.c.status == "running").values(status="queued")
            )

    def claim(self) -> dict[str, Any] | None:
        with self.engine.begin() as conn:
            row = (
                conn.execute(
                    select(sessions)
                    .where(sessions.c.status == "queued")
                    .order_by(sessions.c.created_at)
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if row is None:
                return None
            if row["attempts"] >= 3:
                conn.execute(
                    update(sessions)
                    .where(sessions.c.id == row["id"])
                    .values(status="failed", report={"error": "Recovery retry limit exhausted"})
                )
                return None
            conn.execute(
                update(sessions)
                .where(sessions.c.id == row["id"])
                .values(
                    status="running",
                    attempts=row["attempts"] + 1,
                    updated_at=dt.datetime.now(dt.UTC),
                )
            )
            return dict(row)

    def event(self, identifier: str, event: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            row: list[dict[str, Any]] = conn.execute(
                select(sessions.c.events).where(sessions.c.id == identifier).with_for_update()
            ).scalar_one()
            conn.execute(
                update(sessions)
                .where(sessions.c.id == identifier)
                .values(
                    events=[*row, {"at": dt.datetime.now(dt.UTC).isoformat(), **event}],
                    updated_at=dt.datetime.now(dt.UTC),
                )
            )

    def finish(self, identifier: str, status: str, report: dict[str, Any]) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(sessions)
                .where(sessions.c.id == identifier)
                .values(status=status, report=report, updated_at=dt.datetime.now(dt.UTC))
            )

    def cancel(self, identifier: str) -> bool:
        with self.engine.begin() as conn:
            result = conn.execute(
                update(sessions)
                .where(sessions.c.id == identifier, sessions.c.status.in_(["queued", "running"]))
                .values(cancel_requested=1)
            )
            return bool(result.rowcount)

    def summary(self) -> dict[str, int]:
        with self.engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT count(*) AS total, count(*) FILTER (WHERE "
                        "status='completed') AS completed, "
                        "count(*) FILTER (WHERE report->>'decision'='validated_improvement') "
                        "AS improved, "
                        "count(*) FILTER (WHERE "
                        "report->>'decision'='no_accepted_improvement') AS unchanged, "
                        "count(DISTINCT request->>'workload_id') FILTER (WHERE "
                        "status='completed') AS coverage "
                        "FROM optimization_sessions"
                    )
                )
                .mappings()
                .one()
            )
            return {key: int(value) for key, value in row.items()}
