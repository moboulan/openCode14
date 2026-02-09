"""Tests for the root endpoint and general app behaviour."""

import pytest


@pytest.mark.asyncio
async def test_root_endpoint(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "alert-ingestion"
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
