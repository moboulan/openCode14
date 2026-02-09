"""Tests for the alerts API — POST, GET, list.

All database calls are mocked so these run without PostgreSQL.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
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

    class FakeResponse:
        status_code = 201
        def raise_for_status(self): pass
        def json(self):
            return {"incident_id": fake_incident_id, "id": str(uuid.uuid4())}

    class FakeAsyncClient:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw): return FakeResponse()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([db_sides[0]])(autocommit=True),
        _fake_connection([db_sides[1]])(),
        _fake_connection([None])(autocommit=True),  # link step
    ]):
        with patch("httpx.AsyncClient", FakeAsyncClient):
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


# ── POST /api/v1/alerts — incident service failure (graceful degradation) ──

@pytest.mark.asyncio
async def test_create_alert_incident_service_failure(client, sample_alert_payload):
    """When incident-management is unreachable, the alert is still stored."""
    fake_alert_db_id = uuid.uuid4()

    class FakeAsyncClient:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw): raise Exception("connection refused")

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": fake_alert_db_id}])(autocommit=True),
        _fake_connection([None])(),  # no correlation match
    ]):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] is None
    assert body["action"] == "new_incident"


# ── POST /api/v1/alerts — new incident WITH link step ───────

@pytest.mark.asyncio
async def test_create_alert_new_incident_with_link(client, sample_alert_payload):
    """New incident is created AND the alert↔incident link is written."""
    fake_alert_db_id = uuid.uuid4()
    fake_incident_db_id = str(uuid.uuid4())
    fake_incident_id = "inc-linked"

    class FakeResponse:
        status_code = 201
        def raise_for_status(self): pass
        def json(self):
            return {"incident_id": fake_incident_id, "id": fake_incident_db_id}

    class FakeAsyncClient:
        def __init__(self, **kw): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): pass
        async def post(self, *a, **kw): return FakeResponse()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": fake_alert_db_id}])(autocommit=True),
        _fake_connection([None])(),
        _fake_connection([None, None])(autocommit=True),
    ]):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] == fake_incident_id
    assert body["action"] == "new_incident"


# ── GET /api/v1/alerts/{alert_id} — with incident_id present ─

@pytest.mark.asyncio
async def test_get_alert_with_incident_id(client):
    """Alert that has an incident_id triggers a second DB query."""
    fake_incident_uuid = uuid.uuid4()
    fake_row = {
        "alert_id": "alert-withincident",
        "service": "web",
        "severity": "high",
        "message": "CPU spike",
        "labels": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "incident_id": fake_incident_uuid,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    inc_row = {"incident_id": "inc-resolved"}

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([fake_row])(),
        _fake_connection([inc_row])(),
    ]):
        resp = await client.get("/api/v1/alerts/alert-withincident")

    assert resp.status_code == 200
    assert resp.json()["incident_id"] == "inc-resolved"
