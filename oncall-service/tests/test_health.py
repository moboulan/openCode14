"""Tests for the health router -- /health, /health/ready, /health/live."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_health_check_healthy(client):
    """Health endpoint returns healthy when DB is up."""
    with patch("app.routers.health.check_database_health", return_value=True):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "oncall-service"
        assert "uptime" in body
        assert body["checks"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_degraded(client):
    """Health endpoint returns 503 when DB is down."""
    with patch("app.routers.health.check_database_health", return_value=False):
        resp = await client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["database"] == "unhealthy"


@pytest.mark.asyncio
async def test_health_check_high_memory(client):
    """Health endpoint marks memory as warning when usage exceeds threshold."""
    mock_mem = MagicMock()
    mock_mem.percent = 99.0  # Above default threshold (90)
    with (
        patch("app.routers.health.check_database_health", return_value=True),
        patch("app.routers.health.psutil.virtual_memory", return_value=mock_mem),
    ):
        resp = await client.get("/health")
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["memory"] == "warning"


@pytest.mark.asyncio
async def test_health_check_high_disk(client):
    """Health endpoint marks disk as warning when usage exceeds threshold."""
    mock_disk = MagicMock()
    mock_disk.percent = 99.0  # Above default threshold (90)
    with (
        patch("app.routers.health.check_database_health", return_value=True),
        patch("app.routers.health.psutil.disk_usage", return_value=mock_disk),
    ):
        resp = await client.get("/health")
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["disk"] == "warning"


@pytest.mark.asyncio
async def test_readiness_ready(client):
    """Readiness probe returns ready when DB is up."""
    with patch("app.routers.health.check_database_health", return_value=True):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_not_ready(client):
    """Readiness probe returns not-ready when DB is down."""
    with patch("app.routers.health.check_database_health", return_value=False):
        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "not ready"


@pytest.mark.asyncio
async def test_liveness(client):
    """Liveness probe always returns alive."""
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"
