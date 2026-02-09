"""Tests for notification service health endpoints."""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_health_check_healthy(client):
    """Health endpoint returns 200 when all checks pass."""
    with patch("app.routers.health.check_database_health", return_value=True):
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "notification-service"
    assert "uptime" in body
    assert body["checks"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_db_down(client):
    """Health endpoint returns 503 when DB is down."""
    with patch("app.routers.health.check_database_health", return_value=False):
        resp = await client.get("/health")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["database"] == "unhealthy"


@pytest.mark.asyncio
async def test_readiness_healthy(client):
    """Readiness probe returns ready when DB is up."""
    with patch("app.routers.health.check_database_health", return_value=True):
        resp = await client.get("/health/ready")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_readiness_not_ready(client):
    """Readiness probe returns 503 when DB is down."""
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
