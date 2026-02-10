"""Tests for the FastAPI application setup (main.py)."""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Root endpoint returns service info."""
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "oncall-service"
    assert body["status"] == "running"
    assert "version" in body


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Metrics endpoint returns Prometheus text format."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers.get("content-type", "") or "text/plain" in str(resp.headers)


@pytest.mark.asyncio
async def test_openapi_docs(client):
    """OpenAPI docs should be accessible."""
    resp = await client.get("/docs")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_openapi_json(client):
    """OpenAPI JSON schema should be accessible."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    body = resp.json()
    assert "paths" in body
    assert "/api/v1/schedules" in body["paths"]
    assert "/api/v1/oncall/current" in body["paths"]
    assert "/api/v1/escalate" in body["paths"]
    assert "/api/v1/escalation-policies" in body["paths"]
    assert "/api/v1/check-escalations" in body["paths"]
    assert "/api/v1/metrics/oncall" in body["paths"]


@pytest.mark.asyncio
async def test_process_time_header(client):
    """Middleware adds X-Process-Time header."""
    resp = await client.get("/")
    assert "x-process-time" in resp.headers


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown():
    """Lifespan context manager runs startup and shutdown."""
    from app.main import app, lifespan

    with patch("app.main.close_pool") as mock_close:
        async with lifespan(app):
            pass  # startup happened
        # shutdown happened
        mock_close.assert_called_once()


@pytest.mark.asyncio
async def test_global_exception_handler():
    """Global exception handler returns 500 JSON response."""
    from app.main import global_exception_handler
    from starlette.requests import Request

    scope = {"type": "http", "method": "GET", "path": "/test"}
    mock_request = Request(scope)

    resp = await global_exception_handler(mock_request, RuntimeError("boom"))
    assert resp.status_code == 500
    import json

    body = json.loads(resp.body)
    assert "error" in body
    assert body["error"]["type"] == "RuntimeError"
    assert "timestamp" in body["error"]
