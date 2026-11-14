"""HTTP safety contracts exercised in process without a PostgreSQL service."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from optimizer.api import create_app
from optimizer.config import Settings


@pytest.fixture
def api():
    with patch("optimizer.api.Store") as constructor:
        store = MagicMock()
        constructor.return_value = store
        with TestClient(create_app(Settings())) as client:
            yield client, store


def test_invalid_sql_never_enqueued(api):
    client, store = api
    response = client.post("/api/v1/optimizations", json={"sql": "DELETE FROM commerce.orders"})
    assert response.status_code == 422
    store.create.assert_not_called()


def test_chunked_oversize_body_never_enqueued(api):
    client, store = api
    response = client.post(
        "/api/v1/optimizations",
        content=iter([b'{"sql":"', b"x" * 12000, b"x" * 12000, b'"}']),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    store.create.assert_not_called()


def test_small_chunked_body_delivered_once(api):
    client, store = api
    store.create.return_value = "session-id"
    response = client.post(
        "/api/v1/optimizations",
        content=iter([b'{"sql":', b'"SELECT 1"}']),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 202
    assert response.json()["id"] == "session-id"
    store.create.assert_called_once()


def test_mismatched_workload_never_enqueued(api):
    client, store = api
    response = client.post(
        "/api/v1/optimizations", json={"sql": "SELECT 1", "workload_id": "customer_lookup"}
    )
    assert response.status_code == 422
    store.create.assert_not_called()


def test_remote_api_requires_valid_token():
    token = "test-token-that-is-at-least-32-characters"
    with patch("optimizer.api.Store") as constructor:
        with TestClient(create_app(Settings(deployment="remote", api_token=token))) as client:
            assert client.get("/api/v1/workloads").status_code == 401
            assert (
                client.get(
                    "/api/v1/workloads", headers={"Authorization": "Bearer incorrect"}
                ).status_code
                == 401
            )
            response = client.get("/api/v1/workloads", headers={"Authorization": f"Bearer {token}"})
            assert response.status_code == 200
            assert len(response.json()) == 12
            constructor.return_value.create.assert_not_called()


def test_missing_session_returns_404(api):
    client, store = api
    store.get.return_value = None
    assert client.get("/api/v1/optimizations/missing").status_code == 404


def test_infrastructure_error_does_not_expose_details(api):
    client, store = api
    store.get.side_effect = RuntimeError("private connection configuration")
    # ASGI exception handlers produce the HTTP response, while TestClient normally
    # reraises server exceptions for debugging. Disable that behavior for this check.
    with TestClient(client.app, raise_server_exceptions=False) as caller:
        response = caller.get("/api/v1/optimizations/missing")
    assert response.status_code == 503
    assert "private connection configuration" not in response.text
    assert response.json()["category"] == "RuntimeError"
