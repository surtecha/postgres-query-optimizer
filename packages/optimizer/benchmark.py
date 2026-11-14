import random
import time
from collections.abc import Callable
from typing import Any

from optimizer.database import BudgetExceeded, Database
from optimizer.models import Candidate
from optimizer.plans import compare_plans
from optimizer.statistics import comparison
from optimizer.workloads import WORKLOADS


def benchmark(
    db: Database,
    admin: Any,
    original: str,
    candidate: Candidate,
    candidate_id: str,
    guard: Callable[[], None],
) -> dict[str, Any]:
    samples: dict[str, list[float]] = {"baseline": [], "candidate": []}
    plans: dict[str, Any] = {}
    runs: list[dict[str, Any]] = []
    name = "pgo_exp_" + candidate_id.replace("-", "")[:24]
    ddl = db.index_ddl(admin, candidate.index, name) if candidate.index else None
    index_bytes = 0
    rng = random.Random(42)
    started = time.monotonic()
    protected: dict[str, Any] = {}
    try:
        # Each paired round randomizes order. Index build/drop time is excluded from latency.
        for trial in range(db.settings.repetitions + 2):
            order = ["baseline", "candidate"]
            rng.shuffle(order)
            for label in order:
                guard()
                db.drop_index(admin, name)
                if label == "candidate" and ddl is not None:
                    admin.execute(ddl)
                    index_bytes = admin.execute(
                        "SELECT pg_relation_size(%s::regclass)", ("commerce." + name,)
                    ).fetchone()[0]
                    if index_bytes > db.settings.max_index_bytes:
                        raise BudgetExceeded("Index storage overhead exceeds policy")
                with db.reader() as conn:
                    latency, detail = db.timed(
                        conn, original if label == "baseline" else candidate.sql
                    )
                if trial >= 2:
                    samples[label].append(latency)
                    plans[label] = detail["plan"]
                    runs.append(
                        {
                            "trial": trial - 2,
                            "label": label,
                            "latency_ms": latency,
                            "wall_ms": detail["wall_ms"],
                            "planning_ms": detail["plan"].get("Planning Time"),
                            "buffer_hits": detail["plan"]["Plan"].get("Shared Hit Blocks", 0),
                            "buffer_reads": detail["plan"]["Plan"].get("Shared Read Blocks", 0),
                        }
                    )
        if ddl is not None:
            # Physical design changes must pass the entire protected workload.
            for workload in WORKLOADS:
                guard()
                measured: dict[str, list[float]] = {"baseline": [], "candidate": []}
                for _ in range(5):
                    labels = ["baseline", "candidate"]
                    rng.shuffle(labels)
                    for label in labels:
                        guard()
                        db.drop_index(admin, name)
                        if label == "candidate":
                            admin.execute(ddl)
                        with db.reader() as conn:
                            latency, _detail = db.timed(conn, workload["sql"])
                        measured[label].append(latency)
                protected[workload["id"]] = comparison(measured["baseline"], measured["candidate"])
        return {
            **comparison(samples["baseline"], samples["candidate"]),
            "runs": runs,
            "plans": plans,
            "plan_difference": compare_plans(plans["baseline"], plans["candidate"]),
            "index_bytes": index_bytes,
            "protected": protected,
            "protected_pass": all(r["speedup_ci95"][0] >= 0.9 for r in protected.values()),
            "duration_seconds": time.monotonic() - started,
            "conditions": {
                "seed": 42,
                "warmups": 2,
                "order": "paired randomized",
                "cache": "warm, no OS cache flush",
            },
        }
    finally:
        db.drop_index(admin, name)
