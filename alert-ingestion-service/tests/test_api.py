"""Tests for the alerts API — POST, GET, list.

All database calls are mocked so these run without PostgreSQL.
"""

import pytest
from unittest.mock import patch, MagicMock
from contextlib import contextmanager
from datetime import datetime, timezone
import uuid


# ---------------------------------------------------------------------------
# Helper: build a fake get_db_connection context manager
# ---------------------------------------------------------------------------

def _fake_connection(cursor_sides: list[dict | None]):
    """Return a patched get_db_connection that yields a mock with preset cursor results.

    ``cursor_sides`` is a list of values that successive ``fetchone()`` / ``fetchall()``
    calls will return (one entry per ``with conn.cursor()`` block).
    """
    call_idx = {"i": 0}

    @contextmanager
    def _ctx(autocommit=False):
        conn = MagicMock()

        @contextmanager
        def _cur_ctx():
            cur = MagicMock()
            idx = call_idx["i"]
            if idx < len(cursor_sides):
                val = cursor_sides[idx]
                cur.fetchone.return_value = val
                cur.fetchall.return_value = val if isinstance(val, list) else [val] if val else []
            else:
                cur.fetchone.return_value = None
                cur.fetchall.return_value = []
            call_idx["i"] += 1
            yield cur

        conn.cursor = _cur_ctx
        yield conn

    return _ctx


# ── POST /api/v1/alerts ─────────────────────────────────────

@pytest.mark.asyncio
async def test_create_alert_new_incident(client, sample_alert_payload):
    """Alert with no matching incident → calls incident-management service."""
    fake_alert_db_id = uuid.uuid4()
    fake_incident_id = "inc-aaa111"

    db_sides = [
        {"id": fake_alert_db_id},       # INSERT alert → returns id
        None,                            # correlation SELECT → no match
    ]

    # Mock the external HTTP call to incident-management
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.json.return_value = {
        "incident_id": fake_incident_id,
        "id": str(uuid.uuid4()),
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([db_sides[0]])(autocommit=True),
        _fake_connection([db_sides[1]])(),
        _fake_connection([None])(autocommit=True),  # link step
    ]):
        with patch("httpx.AsyncClient") as MockClient:
            mock_ac = MagicMock()
            mock_ac.__aenter__ = MagicMock(return_value=mock_ac)
            mock_ac.__aexit__ = MagicMock(return_value=False)
            mock_ac.post = MagicMock(return_value=mock_response)
            MockClient.return_value = mock_ac

            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "processed"
    assert body["alert_id"].startswith("alert-")


@pytest.mark.asyncio
async def test_create_alert_correlated_to_existing(client, sample_alert_payload):
    """Alert matches an open incident → correlates."""
    fake_alert_db_id = uuid.uuid4()
    fake_incident_db_id = uuid.uuid4()
    fake_incident_id = "inc-bbb222"

    insert_result = {"id": fake_alert_db_id}
    correlate_result = {"incident_id": fake_incident_id, "id": fake_incident_db_id}

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([insert_result])(autocommit=True),
        _fake_connection([correlate_result])(),
        _fake_connection([None])(autocommit=True),  # link + update
    ]):
        resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["action"] == "existing_incident"
    assert body["incident_id"] == fake_incident_id


# ── POST /api/v1/alerts — validation ────────────────────────

@pytest.mark.asyncio
async def test_create_alert_missing_field(client):
    resp = await client.post("/api/v1/alerts", json={"service": "x"})
    assert resp.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_create_alert_bad_severity(client):
    resp = await client.post(
        "/api/v1/alerts",
        json={"service": "x", "severity": "INVALID", "message": "boom"},
    )
    assert resp.status_code == 422


# ── GET /api/v1/alerts/{alert_id} ────────────────────────────

@pytest.mark.asyncio
async def test_get_alert_found(client):
    fake_row = {
        "alert_id": "alert-abc123",
        "service": "web",
        "severity": "high",
        "message": "CPU spike",
        "labels": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([fake_row])(),
    ]):
        resp = await client.get("/api/v1/alerts/alert-abc123")

    assert resp.status_code == 200
    assert resp.json()["alert_id"] == "alert-abc123"


@pytest.mark.asyncio
async def test_get_alert_not_found(client):
    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([None])(),
    ]):
        resp = await client.get("/api/v1/alerts/alert-nope")
    assert resp.status_code == 404


# ── GET /api/v1/alerts (list) ────────────────────────────────

@pytest.mark.asyncio
async def test_list_alerts(client):
    rows = [
        {
            "alert_id": "alert-111",
            "service": "web",
            "severity": "low",
            "message": "ok",
            "labels": {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "incident_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([rows])(),
    ]):
        resp = await client.get("/api/v1/alerts")

    assert resp.status_code == 200
    body = resp.json()
    assert "alerts" in body
    assert "total" in body


@pytest.mark.asyncio
async def test_list_alerts_with_filter(client):
    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([[]])(),
    ]):
        resp = await client.get("/api/v1/alerts?service=foo&severity=high")
    assert resp.status_code == 200
