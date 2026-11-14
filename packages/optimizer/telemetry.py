import json
import logging
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Histogram

STAGES = Histogram("pgo_stage_seconds", "Workflow stage duration", ["stage", "status"])
CANDIDATES = Counter("pgo_candidates_total", "Generated candidate count", ["provider"])
FAILURES = Counter("pgo_failures_total", "Failures", ["category"])
SESSIONS = Counter("pgo_sessions_total", "Completed sessions", ["decision"])
TOKENS = Counter("pgo_model_tokens_total", "Reported model tokens")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "level": record.levelname,
                "event": record.getMessage(),
                **getattr(record, "fields", {}),
            },
            default=str,
        )


def setup(endpoint: str = "") -> Any:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.getLogger("optimizer").handlers = [handler]
    logging.getLogger("optimizer").setLevel(logging.INFO)
    provider = TracerProvider(
        resource=Resource.create({"service.name": "postgres-query-optimizer"})
    )
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("optimizer")
