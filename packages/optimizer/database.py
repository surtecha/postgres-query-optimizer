"""Least-privilege PostgreSQL reads and controlled local index experiments."""
import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool

from optimizer.config import Settings
from optimizer.dataset import LOCK_ID
from optimizer.models import IndexProposal
from optimizer.safety import TABLES, UnsafeSQL, validate


class BudgetExceeded(RuntimeError):
    pass


class Database:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pool: ConnectionPool[Any] = ConnectionPool(
            settings.read_dsn.get_secret_value(), min_size=1, max_size=3, timeout=5,
            kwargs={"connect_timeout": 5, "application_name": "postgres-query-optimizer-reader"},
            open=False)

    def open(self) -> None:
        self.pool.open(wait=True, timeout=10)

    def close(self) -> None:
        self.pool.close()

    @contextmanager
    def reader(self) -> Generator[Any, None, None]:
        with self.pool.connection() as conn, conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            conn.execute("SELECT set_config('statement_timeout', %s, true)", (str(self.settings.statement_ms),))
            conn.execute("SET LOCAL lock_timeout='1s'")
            conn.execute("SET LOCAL idle_in_transaction_session_timeout='35s'")
            conn.execute("SET LOCAL search_path=pg_catalog,commerce")
            yield conn

    def plan(self, conn: Any, query: str, analyze: bool = False) -> dict[str, Any]:
        validate(query)
        options = "ANALYZE, BUFFERS, TIMING, FORMAT JSON" if analyze else "FORMAT JSON"
        plan: dict[str, Any] = conn.execute(f"EXPLAIN ({options}) " + query).fetchone()[0][0]
        if float(plan["Plan"]["Total Cost"]) > self.settings.max_plan_cost:
            raise BudgetExceeded("Estimated query cost exceeds policy")
        return plan

    def inspect(self, query: str) -> dict[str, Any]:
        tree = validate(query)
        tables = sorted({t.name for t in tree.find_all(__import__('sqlglot').exp.Table) if t.name in TABLES})
        with self.reader() as conn:
            # Parameters constrain catalog access to the requested allowlisted relations.
            columns = conn.execute("SELECT table_name,column_name,data_type FROM information_schema.columns "
                                   "WHERE table_schema='commerce' AND table_name=ANY(%s) ORDER BY table_name,ordinal_position", (tables,)).fetchall()
            indexes = conn.execute("SELECT tablename,indexname,indexdef FROM pg_indexes "
                                   "WHERE schemaname='commerce' AND tablename=ANY(%s)", (tables,)).fetchall()
            statistics = conn.execute("SELECT tablename,attname,null_frac,n_distinct,correlation FROM pg_stats "
                                      "WHERE schemaname='commerce' AND tablename=ANY(%s)", (tables,)).fetchall()
            relations = conn.execute("SELECT c.relname,c.reltuples,c.relpages,s.n_mod_since_analyze,s.last_analyze "
                                    "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                                    "LEFT JOIN pg_stat_all_tables s ON s.relid=c.oid "
                                    "WHERE n.nspname='commerce' AND c.relname=ANY(%s)", (tables,)).fetchall()
            config = conn.execute("SELECT name,setting,unit FROM pg_settings WHERE name=ANY(%s)",
                                  (["server_version", "work_mem", "shared_buffers", "random_page_cost", "jit", "max_parallel_workers_per_gather"],)).fetchall()
            manifest = conn.execute("SELECT seed,orders_count FROM commerce.dataset_manifest").fetchone()
            return {"columns": columns, "indexes": indexes, "statistics": statistics,
                    "relations": [[str(x) for x in row] for row in relations],
                    "config": config, "dataset": manifest}

    @contextmanager
    def experiment_lock(self) -> Generator[Any, None, None]:
        with psycopg.connect(self.settings.admin_dsn.get_secret_value(), autocommit=True,
                             connect_timeout=5, application_name="postgres-query-optimizer-experiment") as admin:
            # Explicit database marker and role prevent accidental arbitrary target execution.
            identity = admin.execute("SELECT current_database(),current_user").fetchone()
            if identity != ("pgo_benchmark", "pgo_experiment"):
                raise UnsafeSQL("Index experiments require pgo_experiment on pgo_benchmark")
            if not admin.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,)).fetchone()[0]:
                raise BudgetExceeded("Another benchmark or dataset generation holds the experiment lock")
            admin.execute("SET statement_timeout='30s'")
            admin.execute("SET lock_timeout='1s'")
            try:
                # A terminated worker may have left a committed experimental index behind.
                stale = admin.execute("SELECT indexname FROM pg_indexes WHERE schemaname='commerce' "
                                      "AND indexname LIKE 'pgo_exp_%%'").fetchall()
                for (name,) in stale:
                    self.drop_index(admin, name)
                yield admin
            finally:
                admin.execute("SELECT pg_advisory_unlock(%s)", (LOCK_ID,))

    def index_ddl(self, admin: Any, proposal: IndexProposal, name: str) -> sql.Composed:
        if proposal.table not in TABLES or not name.startswith("pgo_exp_"):
            raise UnsafeSQL("Index target is not allowed")
        cols = {row[0] for row in admin.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_schema='commerce' AND table_name=%s", (proposal.table,)).fetchall()}
        selected = proposal.columns + proposal.include
        if len(set(selected)) != len(selected) or not set(selected) <= cols:
            raise UnsafeSQL("Invalid or duplicate index columns")
        ddl = sql.SQL("CREATE INDEX {} ON commerce.{} ({})").format(
            sql.Identifier(name), sql.Identifier(proposal.table),
            sql.SQL(", ").join(map(sql.Identifier, proposal.columns)))
        if proposal.include:
            ddl += sql.SQL(" INCLUDE ({})").format(sql.SQL(", ").join(map(sql.Identifier, proposal.include)))
        if proposal.predicate_column is not None:
            if proposal.predicate_column not in cols or proposal.predicate_value is None:
                raise UnsafeSQL("Invalid partial index predicate")
            ddl += sql.SQL(" WHERE {} = {}").format(sql.Identifier(proposal.predicate_column), sql.Literal(proposal.predicate_value))
        return ddl

    def drop_index(self, admin: Any, name: str) -> None:
        if not name.startswith("pgo_exp_"):
            raise UnsafeSQL("Only experimental indexes may be removed")
        admin.execute(sql.SQL("DROP INDEX IF EXISTS commerce.{}").format(sql.Identifier(name)))

    def timed(self, conn: Any, query: str) -> tuple[float, dict[str, Any]]:
        estimate = self.plan(conn, query)
        if estimate["Plan"]["Total Cost"] > self.settings.max_plan_cost:
            raise BudgetExceeded("Estimated cost exceeded")
        start = time.perf_counter()
        plan = self.plan(conn, query, analyze=True)
        # Execution Time is PostgreSQL server time, client wall time is recorded separately.
        return max(float(plan["Execution Time"]), 0.000001), {"plan": plan, "wall_ms": (time.perf_counter()-start)*1000}
