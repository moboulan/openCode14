"""Tests for the root endpoint and general app behaviour."""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_root_endpoint(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "incident-management"
    assert body["version"] == "1.0.0"
    assert body["status"] == "running"


@pytest.mark.asyncio
async def test_process_time_header(client):
    """Middleware should add X-Process-Time header."""
    resp = await client.get("/")
    assert "x-process-time" in resp.headers


@pytest.mark.asyncio
async def test_not_found_returns_404(client):
    resp = await client.get("/does-not-exist")
    assert resp.status_code == 404


# ── Lifespan (startup / shutdown) ────────────────────────────


@pytest.mark.asyncio
async def test_lifespan_startup_shutdown():
    """Lifespan context manager logs startup and calls close_pool on shutdown."""
    from app.main import app, lifespan

    with patch("app.main.close_pool") as mock_close:
        async with lifespan(app):
            pass  # startup complete
        mock_close.assert_called_once()


# ── Global exception handler ─────────────────────────────────


@pytest.mark.asyncio
async def test_global_exception_handler():
    """Unhandled exceptions should return 500 JSON via the global handler."""
    from unittest.mock import MagicMock

    from app.main import global_exception_handler

    mock_request = MagicMock()
    exc = RuntimeError("intentional test error")

    response = await global_exception_handler(mock_request, exc)

    assert response.status_code == 500
    import json

    body = json.loads(response.body)
    assert body["error"]["type"] == "RuntimeError"
    assert body["error"]["message"] == "Internal server error"
    assert "timestamp" in body["error"]
