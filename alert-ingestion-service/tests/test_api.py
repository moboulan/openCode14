"""Tests for the alerts API — POST, GET, list.

All database calls are mocked so these run without PostgreSQL.
"""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from helpers import FakeAsyncClientDown, fake_connection

# ── POST /api/v1/alerts ─────────────────────────────────────


@pytest.mark.asyncio
async def test_create_alert_new_incident(client, sample_alert_payload):
    """Alert with no matching incident → calls incident-management service."""
    fake_alert_db_id = uuid.uuid4()
    fake_incident_id = "inc-aaa111"

    class _Resp:
        status_code = 201

        def raise_for_status(self):
            pass

        def json(self):
            return {"incident_id": fake_incident_id, "id": str(uuid.uuid4())}

    class _Client:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, *a, **kw):
            return _Resp()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": fake_alert_db_id}])(autocommit=True),
            fake_connection([None])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", _Client):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "correlated"
    assert body["action"] == "created_new_incident"
    assert body["alert_id"].startswith("alert-")


@pytest.mark.asyncio
async def test_create_alert_correlated_to_existing(client, sample_alert_payload):
    """Alert matches an open incident → correlates."""
    fake_alert_db_id = uuid.uuid4()
    fake_incident_db_id = uuid.uuid4()
    fake_incident_id = "inc-bbb222"

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": fake_alert_db_id}])(autocommit=True),
            fake_connection(
                [{"incident_id": fake_incident_id, "id": fake_incident_db_id}]
            )(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["action"] == "attached_to_existing_incident"
    assert body["status"] == "correlated"
    assert body["incident_id"] == fake_incident_id


# ── POST /api/v1/alerts — validation ────────────────────────


@pytest.mark.asyncio
async def test_create_alert_missing_field(client):
    resp = await client.post("/api/v1/alerts", json={"service": "x"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_alert_bad_severity(client):
    resp = await client.post(
        "/api/v1/alerts",
        json={"service": "x", "severity": "INVALID", "message": "boom"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_alert_malformed_json(client):
    """Sending non-JSON body should return 422."""
    resp = await client.post(
        "/api/v1/alerts",
        content="this is not json",
        headers={"content-type": "application/json"},
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

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([fake_row])(),
        ],
    ):
        resp = await client.get("/api/v1/alerts/alert-abc123")

    assert resp.status_code == 200
    assert resp.json()["alert_id"] == "alert-abc123"


@pytest.mark.asyncio
async def test_get_alert_not_found(client):
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([None])(),
        ],
    ):
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

    # list_alerts now does: fetchone (COUNT) then fetchall (rows) in ONE cursor
    @contextmanager
    def _list_conn(autocommit=False):
        cur = MagicMock()
        cur.fetchone.return_value = {"cnt": 1}
        cur.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        yield conn

    with patch("app.routers.api.get_db_connection", side_effect=[_list_conn()]):
        resp = await client.get("/api/v1/alerts")

    assert resp.status_code == 200
    body = resp.json()
    assert "alerts" in body
    assert body["total"] == 1
    assert body["limit"] == 100
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_list_alerts_with_filter(client):
    @contextmanager
    def _list_conn(autocommit=False):
        cur = MagicMock()
        cur.fetchone.return_value = {"cnt": 0}
        cur.fetchall.return_value = []
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        yield conn

    with patch("app.routers.api.get_db_connection", side_effect=[_list_conn()]):
        resp = await client.get("/api/v1/alerts?service=foo&severity=high")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_alerts_with_offset(client):
    """Verify offset parameter is accepted and returned."""

    @contextmanager
    def _list_conn(autocommit=False):
        cur = MagicMock()
        cur.fetchone.return_value = {"cnt": 50}
        cur.fetchall.return_value = []
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        yield conn

    with patch("app.routers.api.get_db_connection", side_effect=[_list_conn()]):
        resp = await client.get("/api/v1/alerts?limit=10&offset=20")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 50
    assert body["limit"] == 10
    assert body["offset"] == 20


# ── POST /api/v1/alerts — incident service failure (graceful degradation) ──


@pytest.mark.asyncio
async def test_create_alert_incident_service_failure(client, sample_alert_payload):
    """When incident-management is unreachable, the alert is still stored."""
    fake_alert_db_id = uuid.uuid4()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": fake_alert_db_id}])(autocommit=True),
            fake_connection([None])(),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClientDown):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] is None
    assert body["action"] == "alert_stored_incident_creation_failed"
    assert body["status"] == "created"


@pytest.mark.asyncio
async def test_create_alert_new_incident_with_link(client, sample_alert_payload):
    """New incident is created AND the alert<->incident link is written."""
    fake_alert_db_id = uuid.uuid4()
    fake_incident_db_id = str(uuid.uuid4())
    fake_incident_id = "inc-linked"

    class _Resp:
        status_code = 201

        def raise_for_status(self):
            pass

        def json(self):
            return {"incident_id": fake_incident_id, "id": fake_incident_db_id}

    class _Client:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def post(self, *a, **kw):
            return _Resp()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": fake_alert_db_id}])(autocommit=True),
            fake_connection([None])(),
            fake_connection([None, None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", _Client):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] == fake_incident_id
    assert body["action"] == "created_new_incident"


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

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([fake_row])(),
            fake_connection([inc_row])(),
        ],
    ):
        resp = await client.get("/api/v1/alerts/alert-withincident")

    assert resp.status_code == 200
    assert resp.json()["incident_id"] == "inc-resolved"


# ── GET /metrics — Prometheus endpoint ───────────────────────


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Prometheus /metrics returns 200 and contains custom metric names."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "alerts_received_total" in text
    assert "alerts_correlated_total" in text


# ── DELETE /api/v1/alerts/{alert_id} ─────────────────────────


@pytest.mark.asyncio
async def test_delete_alert_success(client):
    """DELETE existing alert → 204."""
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[fake_connection([{"id": uuid.uuid4()}])(autocommit=True)],
    ):
        resp = await client.delete("/api/v1/alerts/alert-del123")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_alert_not_found(client):
    """DELETE non-existent alert → 404."""
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[fake_connection([None])(autocommit=True)],
    ):
        resp = await client.delete("/api/v1/alerts/alert-nope")
    assert resp.status_code == 404


# ── http_client fallback ─────────────────────────────────────


def test_http_client_fallback():
    """get_http_client() returns a fresh client when not initialised."""
    import app.http_client as hc

    original = hc._client
    try:
        hc._client = None
        c = hc.get_http_client()
        assert c is not None
    finally:
        hc._client = original


def test_http_client_returns_existing():
    """get_http_client() returns the shared client when initialised."""
    import app.http_client as hc

    sentinel = object()
    original = hc._client
    try:
        hc._client = sentinel
        assert hc.get_http_client() is sentinel
    finally:
        hc._client = original
