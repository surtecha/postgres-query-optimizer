import hmac
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text

from optimizer.config import Settings
from optimizer.http_limits import BodyLimit
from optimizer.models import OptimizeRequest
from optimizer.persistence import QueueFull, Store
from optimizer.safety import UnsafeSQL, validate
from optimizer.telemetry import setup
from optimizer.workloads import WORKLOADS, get_workload


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    store = Store(config.app_dsn.get_secret_value())
    tracer = setup(config.otlp_endpoint)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> Any:
        yield
        store.engine.dispose()

    def auth(authorization: str | None = Header(None)) -> None:
        token = config.api_token.get_secret_value()
        if token and not hmac.compare_digest(authorization or "", "Bearer " + token):
            raise HTTPException(401, "Authentication required")

    app = FastAPI(title="PostgreSQL Query Performance Engineer", version="0.1.0", lifespan=lifespan)

    app.add_middleware(BodyLimit)

    @app.middleware("http")
    async def request_id(request: Request, call_next: Any) -> Any:
        identifier = str(uuid.uuid4())
        if (
            request.headers.get("content-length", "0").isdigit()
            and int(request.headers.get("content-length", "0")) > 24000
        ):
            return JSONResponse(
                {"error": "Request too large", "request_id": identifier}, status_code=413
            )
        with tracer.start_as_current_span("http.request") as span:
            span.set_attribute("request.id", identifier)
            response = await call_next(request)
            response.headers["X-Request-ID"] = identifier
            return response

    @app.exception_handler(Exception)
    async def internal_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            {"error": "Internal infrastructure failure", "category": type(exc).__name__},
            status_code=503,
        )

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/readiness", dependencies=[Depends(auth)])
    def readiness() -> dict[str, str]:
        with store.engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM optimization_sessions LIMIT 1"))
        return {"status": "ready"}

    @app.get("/metrics", dependencies=[Depends(auth)])
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/api/v1/summary", dependencies=[Depends(auth)])
    def summary() -> dict[str, int]:
        return store.summary()

    @app.get("/api/v1/workloads", dependencies=[Depends(auth)])
    def workloads() -> list[dict[str, Any]]:
        return WORKLOADS

    @app.get("/api/v1/workloads/{identifier}", dependencies=[Depends(auth)])
    def workload(identifier: str) -> dict[str, Any]:
        try:
            return get_workload(identifier)
        except KeyError as exc:
            raise HTTPException(404, "Workload not found") from exc

    @app.post("/api/v1/optimizations", status_code=202, dependencies=[Depends(auth)])
    def submit(
        body: OptimizeRequest, idempotency_key: str | None = Header(None, max_length=128)
    ) -> dict[str, str]:
        try:
            validate(body.sql)
            if body.workload_id and get_workload(body.workload_id)["sql"] != body.sql:
                raise ValueError("Workload SQL does not match selected workload")
            identifier = store.create(body.model_dump(), idempotency_key, config.max_pending)
        except QueueFull as exc:
            raise HTTPException(429, str(exc)) from exc
        except (UnsafeSQL, ValueError, KeyError) as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"id": identifier, "status_url": f"/api/v1/optimizations/{identifier}"}

    @app.get("/api/v1/optimizations", dependencies=[Depends(auth)])
    @app.get("/api/v1/experiments", dependencies=[Depends(auth)])
    def listing(
        offset: int = Query(0, ge=0),
        limit: int = Query(25, ge=1, le=100),
        status: str | None = Query(None, max_length=24),
    ) -> list[dict[str, Any]]:
        return jsonable_encoder(store.list(offset, limit, status))

    def load(identifier: str) -> dict[str, Any]:
        row = store.get(identifier)
        if row is None:
            raise HTTPException(404, "Optimization not found")
        return jsonable_encoder(row)

    @app.get("/api/v1/optimizations/{identifier}", dependencies=[Depends(auth)])
    @app.get("/api/v1/experiments/{identifier}", dependencies=[Depends(auth)])
    def detail(identifier: str) -> dict[str, Any]:
        return load(identifier)

    @app.post(
        "/api/v1/optimizations/{identifier}/cancel", status_code=202, dependencies=[Depends(auth)]
    )
    def cancel(identifier: str) -> dict[str, Any]:
        load(identifier)
        return {
            "cancellation_requested": store.cancel(identifier),
            "behavior": "Checked between stages and benchmark trials. Active statements "
            "finish or time out.",
        }

    @app.get("/api/v1/optimizations/{identifier}/{section}", dependencies=[Depends(auth)])
    def section(identifier: str, section: str) -> Any:
        row = load(identifier)
        report = row.get("report") or {}
        if section == "events":
            return row["events"]
        if section == "report":
            return report
        candidates = report.get("candidates", [])
        if section == "candidates":
            return candidates
        if section == "benchmarks":
            return [{"id": c["id"], "benchmark": c.get("benchmark")} for c in candidates]
        if section == "plans":
            return {
                "baseline": report.get("baseline_plan"),
                "candidates": [
                    {"id": c["id"], "plans": c.get("benchmark", {}).get("plans")}
                    for c in candidates
                ],
            }
        raise HTTPException(404, "Unknown report section")

    return app
