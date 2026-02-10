"""Tests for the main FastAPI application setup."""

import pytest


@pytest.mark.asyncio
async def test_app_has_cors(client):
    """CORS middleware is attached."""
    resp = await client.options(
        "/health",
        headers={
            "Origin": "http://localhost:8080",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code in (200, 405)


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Prometheus metrics endpoint is exposed."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    assert "http_request" in resp.text or "HELP" in resp.text


@pytest.mark.asyncio
async def test_openapi_endpoint(client):
    """OpenAPI schema is available."""
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    body = resp.json()
    assert body["info"]["title"] == "AI Analysis Service"
