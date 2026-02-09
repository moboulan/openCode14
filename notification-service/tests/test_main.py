"""Tests for the FastAPI application setup (main.py)."""

import pytest


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Root endpoint returns service info."""
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "notification-service"
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
    assert "/api/v1/notify" in body["paths"]
    assert "/api/v1/notifications" in body["paths"]
