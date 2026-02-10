"""Tests for the /health endpoint."""

import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_health_healthy(client, _patch_engine):
    """Health returns 'healthy' when DB check passes."""
    with patch("app.main.check_database_health", return_value=True):
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "ai-analysis-service"
    assert "corpus_size" in body
    assert "knowledge_base_patterns" in body


@pytest.mark.asyncio
async def test_health_degraded(client, _patch_engine):
    """Health returns 'degraded' when DB is unreachable."""
    with patch("app.main.check_database_health", return_value=False):
        resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
