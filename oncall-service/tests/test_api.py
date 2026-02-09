"""Tests for the on-call API -- schedules CRUD, current on-call, escalation."""

import uuid
from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest
from helpers import fake_connection

# ── POST /api/v1/schedules -- create schedule ─────────────────


@pytest.mark.asyncio
async def test_create_schedule(client, sample_schedule_payload):
    """POST /api/v1/schedules creates a schedule and returns 201."""
    fake_row = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice Engineer", "email": "alice@example.com", "primary": True},
            {"name": "Bob Developer", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_row])):
        resp = await client.post("/api/v1/schedules", json=sample_schedule_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["team"] == "platform"
    assert body["rotation_type"] == "weekly"
    assert len(body["engineers"]) == 2


@pytest.mark.asyncio
async def test_create_schedule_validation_error(client):
    """POST /api/v1/schedules rejects empty engineers list."""
    payload = {
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": "2026-01-01",
        "engineers": [],
    }
    resp = await client.post("/api/v1/schedules", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_schedule_db_error(client, sample_schedule_payload):
    """POST /api/v1/schedules returns 500 on DB error."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.post("/api/v1/schedules", json=sample_schedule_payload)
    assert resp.status_code == 500


# ── GET /api/v1/schedules -- list schedules ───────────────────


@pytest.mark.asyncio
async def test_list_schedules(client):
    """GET /api/v1/schedules returns schedule list."""
    fake_rows = [
        {
            "id": str(uuid.uuid4()),
            "team": "platform",
            "rotation_type": "weekly",
            "start_date": date(2026, 1, 1),
            "engineers": [{"name": "Alice", "email": "alice@example.com", "primary": True}],
            "escalation_minutes": 5,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/schedules")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["schedules"][0]["team"] == "platform"


@pytest.mark.asyncio
async def test_list_schedules_with_team_filter(client):
    """GET /api/v1/schedules?team=backend filters by team."""
    fake_rows = [
        {
            "id": str(uuid.uuid4()),
            "team": "backend",
            "rotation_type": "weekly",
            "start_date": date(2026, 1, 1),
            "engineers": [{"name": "Diana", "email": "diana@example.com", "primary": True}],
            "escalation_minutes": 10,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/schedules?team=backend")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["schedules"][0]["team"] == "backend"


@pytest.mark.asyncio
async def test_list_schedules_empty(client):
    """GET /api/v1/schedules returns empty list when none exist."""
    with patch("app.routers.api.get_db_connection", fake_connection([[]])):
        resp = await client.get("/api/v1/schedules")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["schedules"] == []


# ── GET /api/v1/oncall/current -- current on-call ─────────────


@pytest.mark.asyncio
async def test_get_current_oncall(client):
    """GET /api/v1/oncall/current?team=platform returns current on-call."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice Engineer", "email": "alice@example.com", "primary": True},
            {"name": "Bob Developer", "email": "bob@example.com", "primary": False},
            {"name": "Charlie SRE", "email": "charlie@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule])):
        resp = await client.get("/api/v1/oncall/current?team=platform")

    assert resp.status_code == 200
    body = resp.json()
    assert body["team"] == "platform"
    assert body["primary"]["role"] == "primary"
    assert body["secondary"]["role"] == "secondary"
    assert body["escalation_minutes"] == 5


@pytest.mark.asyncio
async def test_get_current_oncall_missing_team(client):
    """GET /api/v1/oncall/current requires team query param."""
    resp = await client.get("/api/v1/oncall/current")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_current_oncall_no_schedule(client):
    """GET /api/v1/oncall/current returns 404 for unknown team."""
    with patch("app.routers.api.get_db_connection", fake_connection([None])):
        resp = await client.get("/api/v1/oncall/current?team=nonexistent")

    assert resp.status_code == 404


# ── POST /api/v1/escalate -- escalate incident ────────────────


@pytest.mark.asyncio
async def test_escalate_incident(client, sample_escalate_payload):
    """POST /api/v1/escalate creates escalation record."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice Engineer", "email": "alice@example.com", "primary": True},
            {"name": "Bob Developer", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    # First call: lookup schedule, second call: insert escalation
    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, None])):
        resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] == "inc-test-123"
    assert "from_engineer" in body
    assert "to_engineer" in body
    assert body["from_engineer"] != body["to_engineer"]


@pytest.mark.asyncio
async def test_escalate_no_schedule(client, sample_escalate_payload):
    """POST /api/v1/escalate returns 404 when no schedule found."""
    with patch("app.routers.api.get_db_connection", fake_connection([None])):
        resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_escalate_single_engineer(client):
    """POST /api/v1/escalate returns 422 when team has only one engineer."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "solo",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice Engineer", "email": "alice@example.com", "primary": True},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule])):
        resp = await client.post(
            "/api/v1/escalate",
            json={"incident_id": "inc-solo", "team": "solo"},
        )

    assert resp.status_code == 422


# ── GET /api/v1/escalations -- list escalation history ────────


@pytest.mark.asyncio
async def test_list_escalations(client):
    """GET /api/v1/escalations returns escalation history."""
    fake_rows = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-123",
            "from_engineer": "alice@example.com",
            "to_engineer": "bob@example.com",
            "reason": "Timeout",
            "escalated_at": datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        }
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["escalations"][0]["incident_id"] == "inc-123"


# ── GET /metrics ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metrics_contains_custom_metrics(client):
    """Metrics endpoint exposes escalations_total and oncall_current."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "escalations_total" in text
