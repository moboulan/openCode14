"""Tests for GET /api/v1/suggestions, GET /api/v1/knowledge-base, POST /api/v1/learn."""

import pytest
from unittest.mock import patch

from helpers import fake_connection, fake_connection_error


# ── GET /suggestions ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggestions_by_incident(client):
    """Fetch suggestions for a specific incident_id."""
    rows = [
        ("Root cause A", "Solution A", 0.92, "knowledge_base", "pattern A"),
        ("Root cause B", "Solution B", 0.65, "historical", "pattern B"),
    ]
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection([rows])):
        resp = await client.get("/api/v1/suggestions", params={"incident_id": "inc-123"})

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert body[0]["root_cause"] == "Root cause A"
    assert body[0]["confidence"] == 0.92
    assert body[1]["source"] == "historical"


@pytest.mark.asyncio
async def test_suggestions_by_alert(client):
    """Fetch suggestions by alert_id."""
    rows = [("Root cause X", "Solution X", 0.78, "knowledge_base", "pattern X")]
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection([rows])):
        resp = await client.get("/api/v1/suggestions", params={"alert_id": "alert-999"})

    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_suggestions_missing_params(client):
    """Suggestions requires at least alert_id or incident_id."""
    resp = await client.get("/api/v1/suggestions")
    assert resp.status_code == 400
    assert "Provide alert_id or incident_id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_suggestions_db_error(client):
    """DB error returns 500."""
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection_error()):
        resp = await client.get("/api/v1/suggestions", params={"incident_id": "inc-1"})
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_suggestions_empty(client):
    """Empty result set returns empty list."""
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection([[]])):
        resp = await client.get("/api/v1/suggestions", params={"incident_id": "inc-none"})
    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /knowledge-base ──────────────────────────────────────

@pytest.mark.asyncio
async def test_knowledge_base_returns_patterns(client):
    """Knowledge-base endpoint returns all static patterns."""
    resp = await client.get("/api/v1/knowledge-base")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) > 0
    # Each entry has the required keys
    for entry in body:
        assert "pattern" in entry
        assert "root_cause" in entry
        assert "solution" in entry
        assert "tags" in entry


# ── POST /learn ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_learn_success(client):
    """Learn stores a new pattern and returns its ID."""
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection([(42,)])):
        resp = await client.post(
            "/api/v1/learn",
            params={
                "message_pattern": "redis connection timeout",
                "root_cause": "Redis instance OOM",
                "solution": "Increase maxmemory or flush stale keys",
                "service": "cache-service",
                "severity": "high",
            },
        )
    assert resp.status_code == 201
    body = resp.json()
    assert body["pattern_id"] == 42
    assert body["status"] == "learned"


@pytest.mark.asyncio
async def test_learn_missing_required_fields(client):
    """Learn rejects empty message_pattern or root_cause."""
    resp = await client.post("/api/v1/learn", params={"message_pattern": "", "root_cause": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_learn_db_error(client):
    """Learn returns 500 on DB failure."""
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection_error()):
        resp = await client.post(
            "/api/v1/learn",
            params={
                "message_pattern": "test pattern",
                "root_cause": "test root cause",
            },
        )
    assert resp.status_code == 500
