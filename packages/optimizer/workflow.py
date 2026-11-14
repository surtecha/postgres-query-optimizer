"""Checkpointed, finite experiment graph. Every execution gate is deterministic."""

import functools
import hashlib
import json
import logging
import time
from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from opentelemetry import trace

from optimizer.benchmark import benchmark
from optimizer.config import Settings
from optimizer.database import BudgetExceeded, Database
from optimizer.equivalence import verify
from optimizer.models import Candidate
from optimizer.persistence import Store
from optimizer.plans import diagnose
from optimizer.providers import DeterministicProvider, OpenAIProvider
from optimizer.safety import UnsafeSQL, fingerprint, normalize, validate
from optimizer.statistics import accept
from optimizer.telemetry import CANDIDATES, FAILURES, SESSIONS, STAGES, TOKENS


class Cancelled(RuntimeError):
    pass


class State(TypedDict, total=False):
    session_id: str
    request: dict[str, Any]
    started_at: float
    fingerprint: str
    metadata: dict[str, Any]
    baseline: dict[str, Any]
    diagnostics: list[dict[str, Any]]
    candidates: list[dict[str, Any]]
    results: list[dict[str, Any]]
    usage: dict[str, Any]
    position: int
    report: dict[str, Any]


class Workflow:
    def __init__(self, db: Database, store: Store, settings: Settings, admin: Any) -> None:
        self.db, self.store, self.settings, self.admin = db, store, settings, admin
        self.tracer = trace.get_tracer("optimizer.workflow")

    def guard(self, state: State) -> None:
        row = self.store.get(state["session_id"])
        if row is None or row["cancel_requested"]:
            raise Cancelled("Cancellation requested")
        if time.time() - state["started_at"] > self.settings.session_seconds:
            raise BudgetExceeded("Session wall-clock budget exceeded")

    def stage(self, name: str, action: Callable[[State], State]) -> Callable[[State], State]:
        @functools.wraps(action)
        def run(state: State) -> State:
            self.guard(state)
            start = time.monotonic()
            status = "ok"
            try:
                with self.tracer.start_as_current_span(name) as span:
                    span.set_attribute("session.id", state["session_id"])
                    return action(state)
            except Exception:
                status = "error"
                FAILURES.labels(name).inc()
                raise
            finally:
                duration = time.monotonic() - start
                STAGES.labels(name, status).observe(duration)
                event = {
                    "stage": name,
                    "tool_name": name,
                    "status": status,
                    "duration_seconds": duration,
                }
                self.store.event(state["session_id"], event)
                logging.getLogger("optimizer").info(
                    "workflow_stage", extra={"fields": {"session_id": state["session_id"], **event}}
                )

        return run

    def validation(self, state: State) -> State:
        return {"fingerprint": fingerprint(state["request"]["sql"])}

    def inspection(self, state: State) -> State:
        return {"metadata": self.db.inspect(state["request"]["sql"])}

    def baseline(self, state: State) -> State:
        with self.db.reader() as conn:
            _, detail = self.db.timed(conn, state["request"]["sql"])
        return {"baseline": detail["plan"], "diagnostics": diagnose(detail["plan"])}

    def generation(self, state: State) -> State:
        query = state["request"]["sql"]
        context = {
            "metadata": state["metadata"],
            "diagnostics": state["diagnostics"],
            "remaining_candidates": self.settings.max_candidates,
            "remaining_seconds": max(
                0, self.settings.session_seconds - (time.time() - state["started_at"])
            ),
        }
        fallback = DeterministicProvider()
        candidates, usage = fallback.generate(query, context, self.settings.max_candidates)
        if state["request"]["provider"] == "openai":
            if self.settings.openai_api_key.get_secret_value():
                proposed, model_usage = OpenAIProvider(self.settings).generate(
                    query, context, self.settings.max_candidates
                )
                candidates = proposed + candidates
                usage = model_usage
            else:
                usage = {
                    **usage,
                    "requested_provider": "openai",
                    "fallback_reason": "No model credential configured",
                }
        seen: set[str] = set()
        unique = []
        for candidate in candidates:
            try:
                key = normalize(candidate.sql) + json.dumps(
                    candidate.index.model_dump() if candidate.index else None, sort_keys=True
                )
            except UnsafeSQL:
                key = candidate.sql
            if key not in seen:
                seen.add(key)
                unique.append(candidate.model_dump())
            if len(unique) == self.settings.max_candidates:
                break
        CANDIDATES.labels(str(usage["provider"])).inc(len(unique))
        if isinstance(usage.get("tokens"), int):
            TOKENS.inc(usage["tokens"])
        return {"candidates": unique, "position": 0, "results": [], "usage": usage}

    def candidate(self, state: State) -> State:
        position = state["position"]
        candidate = Candidate.model_validate(state["candidates"][position])
        identifier = hashlib.sha256((state["session_id"] + str(position)).encode()).hexdigest()[:24]
        result: dict[str, Any] = {"id": identifier, **candidate.model_dump(), "accepted": False}
        try:
            validate(candidate.sql)
            result["safety"] = {"passed": True}
            if candidate.index:
                self.db.index_ddl(self.admin, candidate.index, "pgo_exp_" + identifier)
            with self.db.reader() as conn:
                self.db.plan(conn, candidate.sql)
            result["validation"] = verify(
                self.db, state["request"]["sql"], candidate.sql
            ).model_dump()
            self.guard(state)
            if result["validation"]["status"] == "differentially_validated":
                result["benchmark"] = benchmark(
                    self.db,
                    self.admin,
                    state["request"]["sql"],
                    candidate,
                    identifier,
                    lambda: self.guard(state),
                )
                result["accepted"], result["rejection_reasons"] = accept(
                    result["benchmark"],
                    validated=True,
                    min_improvement=self.settings.min_improvement,
                    max_cv=self.settings.max_cv,
                    index_bytes=result["benchmark"]["index_bytes"],
                    max_index_bytes=self.settings.max_index_bytes,
                    protected_pass=result["benchmark"]["protected_pass"],
                )
            else:
                result["rejection_reasons"] = [result["validation"]["reason"]]
        except (Cancelled, BudgetExceeded):
            raise
        except UnsafeSQL as exc:
            result["safety"] = {"passed": False, "reason": str(exc)}
            result["validation"] = {"status": "statically_rejected", "reason": str(exc)}
            result["rejection_reasons"] = [str(exc)]
        except Exception as exc:
            # Preserve failure category without leaking SQL connection strings or credentials.
            result["error"] = type(exc).__name__
            result["rejection_reasons"] = ["Candidate execution or deterministic validation failed"]
            FAILURES.labels(type(exc).__name__).inc()
        self.store.event(
            state["session_id"],
            {
                "stage": "candidate_result",
                "candidate_id": identifier,
                "accepted": result["accepted"],
                "validation": result.get("validation"),
                "error": result.get("error"),
            },
        )
        return {"position": position + 1, "results": [*state["results"], result]}

    def route(self, state: State) -> str:
        return "candidate" if state["position"] < len(state["candidates"]) else "report"

    def report(self, state: State) -> State:
        valid = [r for r in state["results"] if r["accepted"]]
        best = max(valid, key=lambda r: r["benchmark"]["median_speedup"], default=None)
        decision = "validated_improvement" if best else "no_accepted_improvement"
        report = {
            "session_id": state["session_id"],
            "decision": decision,
            "original_sql": state["request"]["sql"],
            "recommended_sql": best["sql"] if best else state["request"]["sql"],
            "recommended_index": best["index"] if best else None,
            "best_candidate_id": best["id"] if best else None,
            "fingerprint": state["fingerprint"],
            "baseline_plan": state["baseline"],
            "diagnostics": state["diagnostics"],
            "environment": state["metadata"],
            "candidates": state["results"],
            "model_usage": state["usage"],
            "duration_seconds": time.time() - state["started_at"],
            "policy": {
                "min_latency_reduction": self.settings.min_improvement,
                "max_cv": self.settings.max_cv,
                "max_index_bytes": self.settings.max_index_bytes,
                "repetitions": self.settings.repetitions,
                "max_candidates": self.settings.max_candidates,
                "rounds": 1,
                "max_rounds": self.settings.max_rounds,
                "equivalence_required": "differentially_validated",
                "confidence_lower_bound": ">1",
                "protected_index_gate": "all 12 workloads, lower speedup bound >=0.9",
            },
            "limitations": [
                "Finite comparisons do not prove equivalence",
                "Warm cache local measurements",
                "Read workload only, index write amplification is not measured",
                "One proposal round, adaptive model follow-up is not implemented",
            ],
        }
        SESSIONS.labels(decision).inc()
        return {"report": report}

    def compile(self, checkpointer: Any) -> Any:
        graph = StateGraph(State)
        stages = {
            "validation": self.validation,
            "inspection": self.inspection,
            "baseline": self.baseline,
            "generation": self.generation,
            "candidate": self.candidate,
            "report": self.report,
        }
        for name, action in stages.items():
            graph.add_node(name, self.stage(name, action))
        graph.add_edge(START, "validation")
        graph.add_edge("validation", "inspection")
        graph.add_edge("inspection", "baseline")
        graph.add_edge("baseline", "generation")
        graph.add_conditional_edges(
            "generation", self.route, {"candidate": "candidate", "report": "report"}
        )
        graph.add_conditional_edges(
            "candidate", self.route, {"candidate": "candidate", "report": "report"}
        )
        graph.add_edge("report", END)
        return graph.compile(checkpointer=checkpointer)
