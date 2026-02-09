"""Tests for the health router — /health, /health/ready, /health/live."""

from unittest.mock import patch

import pytest

# ── /health/live (no DB needed) ──────────────────────────────


@pytest.mark.asyncio
async def test_liveness_returns_alive(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


# ── /health (DB healthy) ────────────────────────────────────


@pytest.mark.asyncio
async def test_health_healthy(client):
    with patch("app.routers.health.check_database_health", return_value=True), patch(
        "psutil.virtual_memory"
    ) as mock_mem, patch("psutil.disk_usage") as mock_disk:
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.percent = 40.0

        resp = await client.get("/health")
        assert resp.status_code == 200

        body = resp.json()
        assert body["status"] == "healthy"
        assert body["service"] == "incident-management"
        assert body["checks"]["database"] == "healthy"
        assert body["checks"]["memory"] == "healthy"
        assert body["checks"]["disk"] == "healthy"
        assert "uptime" in body
        assert "timestamp" in body


# ── /health (DB unhealthy → 503) ─────────────────────────────


@pytest.mark.asyncio
async def test_health_degraded_when_db_down(client):
    with patch("app.routers.health.check_database_health", return_value=False), patch(
        "psutil.virtual_memory"
    ) as mock_mem, patch("psutil.disk_usage") as mock_disk:
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.percent = 40.0

        resp = await client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["database"] == "unhealthy"


# ── /health (high memory → degraded) ─────────────────────────


@pytest.mark.asyncio
async def test_health_degraded_high_memory(client):
    with patch("app.routers.health.check_database_health", return_value=True), patch(
        "psutil.virtual_memory"
    ) as mock_mem, patch("psutil.disk_usage") as mock_disk:
        mock_mem.return_value.percent = 95.0
        mock_disk.return_value.percent = 40.0

        resp = await client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["memory"] == "warning"


# ── /health (high disk → degraded) ───────────────────────────


@pytest.mark.asyncio
async def test_health_degraded_high_disk(client):
    with patch("app.routers.health.check_database_health", return_value=True), patch(
        "psutil.virtual_memory"
    ) as mock_mem, patch("psutil.disk_usage") as mock_disk:
        mock_mem.return_value.percent = 50.0
        mock_disk.return_value.percent = 95.0

        resp = await client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["disk"] == "warning"


# ── /health/ready (DB healthy) ───────────────────────────────


@pytest.mark.asyncio
async def test_readiness_ready(client):
    with patch("app.routers.health.check_database_health", return_value=True):
        resp = await client.get("/health/ready")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"


# ── /health/ready (DB unhealthy → 503) ───────────────────────


@pytest.mark.asyncio
async def test_readiness_not_ready(client):
    with patch("app.routers.health.check_database_health", return_value=False):
        resp = await client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["status"] == "not ready"
