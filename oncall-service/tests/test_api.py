"""Tests for the on-call API -- schedules CRUD, current on-call, escalation, policies, metrics."""

import json
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from helpers import FakeAsyncClient, FakeAsyncClientDown, fake_connection, make_fake_async_client

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

    # DB calls: 1) lookup schedule, 2) insert escalation, 3) deactivate timer,
    # 4) lookup policy for timer, 5) insert timer
    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, None, None, None, None])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] == "inc-test-123"
    assert "from_engineer" in body
    assert "to_engineer" in body
    assert body["from_engineer"] != body["to_engineer"]
    assert body["level"] == 1


@pytest.mark.asyncio
async def test_escalate_no_schedule(client, sample_escalate_payload):
    """POST /api/v1/escalate returns 404 when no schedule found."""
    with patch("app.routers.api.get_db_connection", fake_connection([None])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_escalate_single_engineer(client):
    """POST /api/v1/escalate with single engineer escalates to manager."""
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

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, None, None, None, None])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post(
                "/api/v1/escalate",
                json={"incident_id": "inc-solo", "team": "solo"},
            )

    # Single-engineer teams now escalate to manager instead of returning 422
    assert resp.status_code == 201
    body = resp.json()
    assert body["to_engineer"] == "admin@example.com"


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
            "level": 1,
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
    assert body["escalations"][0]["level"] == 1


# ── POST /api/v1/escalation-policies -- create policy ────────


@pytest.mark.asyncio
async def test_create_escalation_policy(client):
    """POST /api/v1/escalation-policies creates a policy."""
    payload = {
        "team": "platform",
        "levels": [
            {"level": 1, "wait_minutes": 5, "notify_target": "secondary"},
            {"level": 2, "wait_minutes": 10, "notify_target": "manager"},
        ],
    }

    with patch("app.routers.api.get_db_connection", fake_connection([None, None, None])):
        resp = await client.post("/api/v1/escalation-policies", json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["team"] == "platform"
    assert len(body["levels"]) == 2
    assert body["levels"][0]["wait_minutes"] == 5


@pytest.mark.asyncio
async def test_create_escalation_policy_validation_error(client):
    """POST /api/v1/escalation-policies rejects empty levels."""
    payload = {"team": "platform", "levels": []}
    resp = await client.post("/api/v1/escalation-policies", json=payload)
    assert resp.status_code == 422


# ── GET /api/v1/escalation-policies -- list policies ─────────


@pytest.mark.asyncio
async def test_list_escalation_policies(client):
    """GET /api/v1/escalation-policies returns policy list."""
    fake_rows = [
        {"team": "platform", "level": 1, "wait_minutes": 5, "notify_target": "secondary"},
        {"team": "platform", "level": 2, "wait_minutes": 10, "notify_target": "manager"},
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/escalation-policies")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert len(body["policies"][0]["levels"]) == 2


# ── GET /api/v1/escalation-policies/{team} -- get policy ─────


@pytest.mark.asyncio
async def test_get_escalation_policy(client):
    """GET /api/v1/escalation-policies/platform returns the team policy."""
    fake_rows = [
        {"team": "platform", "level": 1, "wait_minutes": 5, "notify_target": "secondary"},
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/escalation-policies/platform")

    assert resp.status_code == 200
    body = resp.json()
    assert body["team"] == "platform"


@pytest.mark.asyncio
async def test_get_escalation_policy_not_found(client):
    """GET /api/v1/escalation-policies/nonexistent returns 404."""
    with patch("app.routers.api.get_db_connection", fake_connection([[]])):
        resp = await client.get("/api/v1/escalation-policies/nonexistent")

    assert resp.status_code == 404


# ── POST /api/v1/check-escalations -- auto escalation ────────


@pytest.mark.asyncio
async def test_check_escalations_no_timers(client):
    """POST /api/v1/check-escalations returns empty when no expired timers."""
    with patch("app.routers.api.get_db_connection", fake_connection([[]])):
        resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 0
    assert body["escalated"] == 0


@pytest.mark.asyncio
async def test_check_escalations_with_expired_timer(client):
    """POST /api/v1/check-escalations escalates expired timers."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-expired-1",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    fake_policy = {"wait_minutes": 5, "notify_target": "secondary"}

    # DB calls: 1) get expired timers, 2) get schedule, 3) get policy,
    # 4) insert escalation + deactivate timer, 5) lookup policy for new timer, 6) insert timer
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, fake_policy, None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 1
    assert body["escalated"] == 1
    assert body["details"][0]["action"] == "escalated"


# ── GET /api/v1/metrics/oncall -- on-call metrics ────────────


@pytest.mark.asyncio
async def test_get_oncall_metrics(client):
    """GET /api/v1/metrics/oncall returns on-call metrics."""
    fake_esc_count = {"cnt": 5}
    fake_esc_by_team = [{"team": "platform", "cnt": 3}]
    fake_incident_summary = {"total": 50, "avg_mtta": 180.0, "avg_mttr": 900.0}
    fake_load = [{"assigned_to": "Alice", "cnt": 3}]

    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_esc_count, fake_esc_by_team, fake_incident_summary, fake_load]),
    ):
        resp = await client.get("/api/v1/metrics/oncall")

    assert resp.status_code == 200
    body = resp.json()
    assert "total_escalations" in body
    assert "escalation_rate_pct" in body
    assert "avg_mtta_seconds" in body


# ── POST /api/v1/escalate with level 2 ───────────────────────


@pytest.mark.asyncio
async def test_escalate_level_2_to_manager(client):
    """POST /api/v1/escalate with level=2 escalates to manager."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, None, None, None, None])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post(
                "/api/v1/escalate",
                json={
                    "incident_id": "inc-l2",
                    "team": "platform",
                    "level": 2,
                    "reason": "Secondary did not respond",
                },
            )

    assert resp.status_code == 201
    body = resp.json()
    assert body["level"] == 2
    assert body["to_engineer"] == "admin@example.com"


# ── GET /metrics ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_metrics_contains_custom_metrics(client):
    """Metrics endpoint exposes escalations_total and oncall_current."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "escalations_total" in text


# ══════════════════════════════════════════════════════════════
# String-engineers branches (json.loads path)
# ══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_schedule_string_engineers(client, sample_schedule_payload):
    """POST /api/v1/schedules handles engineers returned as a JSON string."""
    fake_row = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": json.dumps(
            [
                {"name": "Alice Engineer", "email": "alice@example.com", "primary": True},
            ]
        ),
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_row])):
        resp = await client.post("/api/v1/schedules", json=sample_schedule_payload)

    assert resp.status_code == 201
    assert len(resp.json()["engineers"]) == 1


@pytest.mark.asyncio
async def test_list_schedules_string_engineers(client):
    """GET /api/v1/schedules handles engineers stored as JSON string."""
    fake_rows = [
        {
            "id": str(uuid.uuid4()),
            "team": "platform",
            "rotation_type": "weekly",
            "start_date": date(2026, 1, 1),
            "engineers": json.dumps([{"name": "Alice", "email": "alice@example.com", "primary": True}]),
            "escalation_minutes": 5,
            "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        }
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/schedules")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_current_oncall_string_engineers(client):
    """GET /api/v1/oncall/current handles engineers stored as JSON string."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": json.dumps(
            [
                {"name": "Alice", "email": "alice@example.com", "primary": True},
                {"name": "Bob", "email": "bob@example.com", "primary": False},
            ]
        ),
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule])):
        resp = await client.get("/api/v1/oncall/current?team=platform")

    assert resp.status_code == 200
    assert resp.json()["primary"]["role"] == "primary"


# ══════════════════════════════════════════════════════════════
# DB-error paths
# ══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_list_schedules_db_error(client):
    """GET /api/v1/schedules returns 500 on DB error."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.get("/api/v1/schedules")
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_current_oncall_db_error(client):
    """GET /api/v1/oncall/current returns 500 on DB error."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.get("/api/v1/oncall/current?team=platform")
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_get_current_oncall_empty_engineers(client):
    """GET /api/v1/oncall/current returns 404 when schedule has no engineers."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule])):
        resp = await client.get("/api/v1/oncall/current?team=platform")
    assert resp.status_code == 404
    assert "No engineers" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_escalate_db_error_schedule_lookup(client, sample_escalate_payload):
    """POST /api/v1/escalate returns 500 when schedule lookup fails."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_escalate_empty_engineers(client, sample_escalate_payload):
    """POST /api/v1/escalate returns 404 when schedule has no engineers."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_escalate_no_team_defaults_to_platform(client):
    """POST /api/v1/escalate defaults team to 'platform' when missing."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, None, None, None, None])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post(
                "/api/v1/escalate",
                json={"incident_id": "inc-no-team", "team": None},
            )
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_escalate_db_error_recording(client, sample_escalate_payload):
    """POST /api/v1/escalate returns 500 when recording the escalation fails."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    # 1) schedule lookup OK, 2) insert escalation FAIL
    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, Exception("DB down")])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_escalate_deactivate_timer_error(client, sample_escalate_payload):
    """POST /api/v1/escalate succeeds even when deactivating timers fails (non-critical)."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    # 1) schedule OK, 2) insert escalation OK, 3) deactivate timer FAIL, 4) timer policy OK, 5) timer insert OK
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_schedule, None, Exception("DB down"), None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_escalate_timer_errors(client, sample_escalate_payload):
    """POST /api/v1/escalate succeeds even when timer creation fails."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    # 1) schedule OK, 2) insert esc OK, 3) deactivate OK, 4) timer policy FAIL, 5) timer insert FAIL
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_schedule, None, None, Exception("DB"), Exception("DB")]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_escalate_notification_failure(client, sample_escalate_payload):
    """POST /api/v1/escalate succeeds even when notification service is down."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, None, None, None, None])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClientDown):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_escalate_notification_bad_response(client, sample_escalate_payload):
    """POST /api/v1/escalate handles notification service returning 4xx."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    BadClient = make_fake_async_client(post_status=500)
    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule, None, None, None, None])):
        with patch("app.routers.api.httpx.AsyncClient", BadClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_escalations_db_error(client):
    """GET /api/v1/escalations returns 500 on DB error."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.get("/api/v1/escalations")
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_list_escalations_with_incident_filter(client):
    """GET /api/v1/escalations?incident_id=... filters properly."""
    fake_rows = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-filter",
            "from_engineer": "alice@example.com",
            "to_engineer": "bob@example.com",
            "level": 1,
            "reason": "Timeout",
            "escalated_at": datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
        }
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/escalations?incident_id=inc-filter")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


# ── Escalation policy error paths ────────────────────────────


@pytest.mark.asyncio
async def test_create_policy_db_error(client, sample_policy_payload):
    """POST /api/v1/escalation-policies returns 500 on DB error."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.post("/api/v1/escalation-policies", json=sample_policy_payload)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_list_policies_db_error(client):
    """GET /api/v1/escalation-policies returns 500 on DB error."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.get("/api/v1/escalation-policies")
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_list_policies_with_team_filter(client):
    """GET /api/v1/escalation-policies?team=backend filters by team."""
    fake_rows = [
        {"team": "backend", "level": 1, "wait_minutes": 10, "notify_target": "secondary"},
    ]

    with patch("app.routers.api.get_db_connection", fake_connection([fake_rows])):
        resp = await client.get("/api/v1/escalation-policies?team=backend")

    assert resp.status_code == 200
    assert resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_get_policy_db_error(client):
    """GET /api/v1/escalation-policies/platform returns 500 on DB error."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.get("/api/v1/escalation-policies/platform")
    assert resp.status_code == 500


# ══════════════════════════════════════════════════════════════
# check-escalations — exhaustive branch coverage
# ══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_check_escalations_db_error(client):
    """POST /api/v1/check-escalations returns 500 when timer query fails."""
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.post("/api/v1/check-escalations")
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_check_escalations_incident_acknowledged(client):
    """POST /api/v1/check-escalations skips acknowledged incidents."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-ack",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    # httpx returns acknowledged status
    AckClient = make_fake_async_client(get_json={"status": "acknowledged"})

    # 1) get timers, 2) deactivate timer (for acknowledged)
    with patch("app.routers.api.get_db_connection", fake_connection([fake_timers, None])):
        with patch("app.routers.api.httpx.AsyncClient", AckClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 1
    assert body["escalated"] == 0
    assert body["details"][0]["action"] == "skipped"
    assert "acknowledged" in body["details"][0]["reason"]


@pytest.mark.asyncio
async def test_check_escalations_incident_ack_deactivate_error(client):
    """POST /api/v1/check-escalations handles DB error when deactivating acknowledged timer."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-ack-err",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    AckClient = make_fake_async_client(get_json={"status": "resolved"})

    # 1) get timers OK, 2) deactivate timer FAIL (non-critical)
    with patch("app.routers.api.get_db_connection", fake_connection([fake_timers, Exception("DB")])):
        with patch("app.routers.api.httpx.AsyncClient", AckClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["details"][0]["action"] == "skipped"


@pytest.mark.asyncio
async def test_check_escalations_httpx_error(client):
    """POST /api/v1/check-escalations handles httpx failure when checking incident."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-http-err",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    fake_policy = {"wait_minutes": 5, "notify_target": "secondary"}

    # httpx GET raises
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, fake_policy, None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClientDown):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] == 1


@pytest.mark.asyncio
async def test_check_escalations_no_schedule(client):
    """POST /api/v1/check-escalations skips timers with no schedule."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-no-sched",
            "team": "orphaned",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    # 1) get timers, 2) schedule lookup returns None
    with patch("app.routers.api.get_db_connection", fake_connection([fake_timers, None])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 1
    assert body["escalated"] == 0
    assert body["details"][0]["action"] == "skipped"
    assert "No schedule" in body["details"][0]["reason"]


@pytest.mark.asyncio
async def test_check_escalations_schedule_lookup_error(client):
    """POST /api/v1/check-escalations skips timer when schedule lookup raises."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-sched-err",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    # 1) get timers OK, 2) schedule lookup FAIL → schedule=None → skip
    with patch("app.routers.api.get_db_connection", fake_connection([fake_timers, Exception("DB")])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["details"][0]["action"] == "skipped"


@pytest.mark.asyncio
async def test_check_escalations_policy_manager_target(client):
    """POST /api/v1/check-escalations escalates to manager when policy says so."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-mgr",
            "team": "platform",
            "current_level": 2,
            "assigned_to": "bob@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    fake_policy = {"wait_minutes": 10, "notify_target": "manager"}

    # 1) timers, 2) schedule, 3) policy, 4) record escalation, 5) timer policy, 6) timer insert
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, fake_policy, None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] == 1
    assert body["details"][0]["to"] == "admin@example.com"


@pytest.mark.asyncio
async def test_check_escalations_policy_direct_email(client):
    """POST /api/v1/check-escalations escalates to direct email from policy."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-direct",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    fake_policy = {"wait_minutes": 5, "notify_target": "teamlead@example.com"}

    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, fake_policy, None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["details"][0]["to"] == "teamlead@example.com"


@pytest.mark.asyncio
async def test_check_escalations_no_policy_level_gt1(client):
    """POST /api/v1/check-escalations defaults to manager when no policy and level > 1."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-nopol",
            "team": "platform",
            "current_level": 3,
            "assigned_to": "bob@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    # No policy found (None)
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, None, None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["details"][0]["to"] == "admin@example.com"


@pytest.mark.asyncio
async def test_check_escalations_no_policy_level1_secondary(client):
    """POST /api/v1/check-escalations defaults to secondary when no policy and level == 1."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-nopol-l1",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, None, None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    # The actual secondary depends on rotation index at today's date
    assert body["details"][0]["to"] in ("alice@example.com", "bob@example.com")


@pytest.mark.asyncio
async def test_check_escalations_policy_lookup_error(client):
    """POST /api/v1/check-escalations handles DB error in policy lookup."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-pol-err",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    # 1) timers, 2) schedule, 3) policy FAIL → policy_row=None, 4) record, 5) timer policy, 6) timer insert
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, Exception("DB"), None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] == 1


@pytest.mark.asyncio
async def test_check_escalations_record_error(client):
    """POST /api/v1/check-escalations skips timer when recording escalation fails."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-rec-err",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    fake_policy = {"wait_minutes": 5, "notify_target": "secondary"}

    # 1) timers, 2) schedule, 3) policy, 4) record escalation FAIL → continue
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, fake_policy, Exception("DB")]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["checked"] == 1
    assert body["escalated"] == 0


@pytest.mark.asyncio
async def test_check_escalations_max_level_no_timer(client):
    """POST /api/v1/check-escalations does not start timer when max level exceeded."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-maxlvl",
            "team": "platform",
            "current_level": 99,  # Way above ESCALATION_LOOP_COUNT + 1
            "assigned_to": "admin@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    fake_policy = {"wait_minutes": 5, "notify_target": "manager"}

    # 1) timers, 2) schedule, 3) policy, 4) record escalation (no timer calls after)
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, fake_policy, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] == 1


@pytest.mark.asyncio
async def test_check_escalations_incident_404(client):
    """POST /api/v1/check-escalations proceeds when incident service returns non-200."""
    fake_timers = [
        {
            "id": str(uuid.uuid4()),
            "incident_id": "inc-404",
            "team": "platform",
            "current_level": 1,
            "assigned_to": "alice@example.com",
        }
    ]

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    fake_policy = {"wait_minutes": 5, "notify_target": "secondary"}

    # Incident service returns 404 → incident_status stays None → escalate
    Client404 = make_fake_async_client(get_status=404, get_json={})

    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_timers, fake_schedule, fake_policy, None, None, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", Client404):
            resp = await client.post("/api/v1/check-escalations")

    assert resp.status_code == 200
    body = resp.json()
    assert body["escalated"] == 1


# ══════════════════════════════════════════════════════════════
# metrics/oncall — error paths
# ══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_oncall_metrics_escalation_db_error(client):
    """GET /api/v1/metrics/oncall handles DB error in escalation query gracefully."""
    # Both DB connections fail → all metrics are defaults
    with patch("app.routers.api.get_db_connection", side_effect=Exception("DB down")):
        resp = await client.get("/api/v1/metrics/oncall")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_escalations"] == 0
    assert body["total_incidents"] == 0


@pytest.mark.asyncio
async def test_oncall_metrics_incident_db_error(client):
    """GET /api/v1/metrics/oncall handles DB error in incident query gracefully."""
    fake_esc_count = {"cnt": 3}
    fake_esc_by_team = []  # No team data

    # 1) escalation count OK, 2) incident query FAIL
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_esc_count, Exception("DB down")]),
    ):
        resp = await client.get("/api/v1/metrics/oncall")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_escalations"] == 3
    assert body["total_incidents"] == 0


@pytest.mark.asyncio
async def test_oncall_metrics_full_data(client):
    """GET /api/v1/metrics/oncall returns full metrics when all queries succeed."""
    from unittest.mock import call

    fake_esc_count = {"cnt": 10}
    fake_esc_by_team = [{"team": "platform", "cnt": 7}]

    fake_incident_summary = {"total": 100, "avg_mtta": 120.5, "avg_mttr": 600.0}
    fake_load = [{"assigned_to": "alice@example.com", "cnt": 5}]

    # We need a special mock that returns different values for fetchone vs fetchall
    # within the same cursor. Let's create a custom mock.
    call_idx = {"i": 0}

    from contextlib import contextmanager
    from unittest.mock import MagicMock

    @contextmanager
    def _fake_conn(autocommit=False):
        conn = MagicMock()

        @contextmanager
        def _cur():
            cur = MagicMock()
            idx = call_idx["i"]
            if idx == 0:
                # First cursor: escalation count + by-team
                cur.fetchone.return_value = fake_esc_count
                cur.fetchall.return_value = fake_esc_by_team
            elif idx == 1:
                # Second cursor: incident summary + load
                cur.fetchone.return_value = fake_incident_summary
                cur.fetchall.return_value = fake_load
            call_idx["i"] += 1
            yield cur

        conn.cursor = _cur
        yield conn

    with patch("app.routers.api.get_db_connection", _fake_conn):
        resp = await client.get("/api/v1/metrics/oncall")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_escalations"] == 10
    assert body["total_incidents"] == 100
    assert body["avg_mtta_seconds"] == 120.5
    assert body["avg_mttr_seconds"] == 600.0
    assert body["escalation_rate_pct"] == 10.0
    assert body["oncall_load"]["alice@example.com"] == 5
    assert body["by_team"]["platform"] == 7


@pytest.mark.asyncio
async def test_oncall_metrics_zero_incidents(client):
    """GET /api/v1/metrics/oncall handles zero total incidents (no divide-by-zero)."""
    from contextlib import contextmanager
    from unittest.mock import MagicMock

    call_idx = {"i": 0}

    fake_esc_count = {"cnt": 0}
    fake_incident_summary = {"total": 0, "avg_mtta": None, "avg_mttr": None}

    @contextmanager
    def _fake_conn(autocommit=False):
        conn = MagicMock()

        @contextmanager
        def _cur():
            cur = MagicMock()
            idx = call_idx["i"]
            if idx == 0:
                cur.fetchone.return_value = fake_esc_count
                cur.fetchall.return_value = []
            elif idx == 1:
                cur.fetchone.return_value = fake_incident_summary
                cur.fetchall.return_value = []
            call_idx["i"] += 1
            yield cur

        conn.cursor = _cur
        yield conn

    with patch("app.routers.api.get_db_connection", _fake_conn):
        resp = await client.get("/api/v1/metrics/oncall")

    assert resp.status_code == 200
    body = resp.json()
    assert body["escalation_rate_pct"] is None
    assert body["avg_mtta_seconds"] is None


# ══════════════════════════════════════════════════════════════
# Edge-case coverage -- remaining lines
# ══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_oncall_empty_engineers_json_string(client):
    """GET /api/v1/oncall/current returns 404 when engineers is JSON string '[]'."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": "[]",  # valid JSON string that parses to empty list
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule])):
        resp = await client.get("/api/v1/oncall/current?team=platform")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_escalate_no_to_engineer(client):
    """POST /api/v1/escalate returns 422 when to_engineer resolves to empty."""
    from app.config import settings as _s

    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "solo",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    with patch("app.routers.api.get_db_connection", fake_connection([fake_schedule])):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            with patch.object(_s, "MANAGER_EMAIL", ""):
                resp = await client.post(
                    "/api/v1/escalate",
                    json={"incident_id": "inc-no-target", "team": "solo"},
                )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_escalate_timer_uses_policy_wait(client, sample_escalate_payload):
    """POST /api/v1/escalate _start_escalation_timer reads wait_minutes from policy."""
    fake_schedule = {
        "id": str(uuid.uuid4()),
        "team": "platform",
        "rotation_type": "weekly",
        "start_date": date(2026, 1, 1),
        "engineers": [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
        ],
        "escalation_minutes": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
    }

    timer_policy = {"wait_minutes": 15}

    # 1) schedule, 2) insert esc, 3) deactivate timer, 4) timer policy FOUND, 5) timer insert
    with patch(
        "app.routers.api.get_db_connection",
        fake_connection([fake_schedule, None, None, timer_policy, None]),
    ):
        with patch("app.routers.api.httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/escalate", json=sample_escalate_payload)
    assert resp.status_code == 201
