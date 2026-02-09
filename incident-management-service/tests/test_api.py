"""Tests for the incidents API — POST, GET, list, PATCH, metrics, analytics.

All database calls are mocked so these run without PostgreSQL.
"""

import pytest
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from helpers import fake_connection as _fake_connection


# Simulate external services being down
class _FakeAsyncClientDown:
    def __init__(self, **kw):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *a):
        pass
    async def get(self, *a, **kw):
        raise Exception("connection refused")
    async def post(self, *a, **kw):
        raise Exception("connection refused")


def _make_incident_row(
    incident_id="inc-test123",
    severity="low",
    status="open",
    assigned_to=None,
    notes="[]",
    acknowledged_at=None,
    resolved_at=None,
):
    """Build a dict mimicking a DB row from incidents.incidents."""
    now = datetime.now(timezone.utc)
    return {
        "id": uuid.uuid4(),
        "incident_id": incident_id,
        "title": "[LOW] test-svc: Unit test",
        "description": "test",
        "service": "test-svc",
        "severity": severity,
        "status": status,
        "assigned_to": assigned_to,
        "notes": notes,
        "created_at": now - timedelta(minutes=10),
        "acknowledged_at": acknowledged_at,
        "resolved_at": resolved_at,
        "updated_at": now,
    }


# ── POST /api/v1/incidents ───────────────────────────────────

@pytest.mark.asyncio
async def test_create_incident(client, sample_incident_payload):
    """Creating an incident stores it and returns 201."""
    row = _make_incident_row()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(autocommit=True),   # INSERT
    ]):
        with patch("httpx.AsyncClient", _FakeAsyncClientDown):
            resp = await client.post("/api/v1/incidents", json=sample_incident_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "open"
    assert body["service"] == "test-svc"


@pytest.mark.asyncio
async def test_create_incident_validation_error(client):
    """Missing required fields returns 422."""
    resp = await client.post("/api/v1/incidents", json={"title": "X"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_incident_bad_severity(client):
    resp = await client.post(
        "/api/v1/incidents",
        json={"title": "X", "service": "x", "severity": "INVALID"},
    )
    assert resp.status_code == 422


# ── GET /api/v1/incidents (list) ─────────────────────────────

def _list_connection(total: int, rows: list):
    """Return a get_db_connection CM whose cursor serves COUNT then SELECT."""
    @contextmanager
    def _ctx(autocommit=False):
        fetch_one_results = iter([{"cnt": total}])
        fetch_all_results = iter([rows])

        cur = MagicMock()
        cur.fetchone = MagicMock(side_effect=lambda: next(fetch_one_results))
        cur.fetchall = MagicMock(side_effect=lambda: next(fetch_all_results))

        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        yield conn
    return _ctx


@pytest.mark.asyncio
async def test_list_incidents(client):
    rows = [_make_incident_row()]

    with patch("app.routers.api.get_db_connection", side_effect=[
        _list_connection(total=1, rows=rows)(),
    ]):
        resp = await client.get("/api/v1/incidents")

    assert resp.status_code == 200
    body = resp.json()
    assert "incidents" in body
    assert body["total"] == 1
    assert "limit" in body
    assert "offset" in body


@pytest.mark.asyncio
async def test_list_incidents_with_filters(client):
    with patch("app.routers.api.get_db_connection", side_effect=[
        _list_connection(total=0, rows=[])(),
    ]):
        resp = await client.get("/api/v1/incidents?status=open&severity=high&service=web")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


# ── GET /api/v1/incidents/{incident_id} ──────────────────────

@pytest.mark.asyncio
async def test_get_incident_found(client):
    row = _make_incident_row(incident_id="inc-found")

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(),          # incident row
        _fake_connection([[]])(),            # linked alerts (empty)
    ]):
        resp = await client.get("/api/v1/incidents/inc-found")

    assert resp.status_code == 200
    body = resp.json()
    assert body["incident_id"] == "inc-found"
    assert "alerts" in body


@pytest.mark.asyncio
async def test_get_incident_not_found(client):
    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([None])(),
    ]):
        resp = await client.get("/api/v1/incidents/inc-nope")
    assert resp.status_code == 404


# ── PATCH /api/v1/incidents/{incident_id} — acknowledge ──────

@pytest.mark.asyncio
async def test_patch_acknowledge(client):
    """Acknowledging sets acknowledged_at and returns updated incident."""
    now = datetime.now(timezone.utc)
    row = _make_incident_row(incident_id="inc-ack", status="open")
    updated = _make_incident_row(incident_id="inc-ack", status="acknowledged", acknowledged_at=now)

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(),                    # fetch current
        _fake_connection([updated])(autocommit=True),  # UPDATE RETURNING
    ]):
        resp = await client.patch(
            "/api/v1/incidents/inc-ack",
            json={"status": "acknowledged"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "acknowledged"


# ── PATCH — resolve ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_resolve(client):
    """Resolving sets resolved_at and returns updated incident."""
    now = datetime.now(timezone.utc)
    row = _make_incident_row(
        incident_id="inc-res",
        status="acknowledged",
        acknowledged_at=now - timedelta(minutes=5),
    )
    updated = _make_incident_row(
        incident_id="inc-res",
        status="resolved",
        acknowledged_at=now - timedelta(minutes=5),
        resolved_at=now,
    )

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(),
        _fake_connection([updated])(autocommit=True),
    ]):
        resp = await client.patch(
            "/api/v1/incidents/inc-res",
            json={"status": "resolved"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


# ── PATCH — add note ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_add_note(client):
    row = _make_incident_row(incident_id="inc-note")
    updated = _make_incident_row(incident_id="inc-note")
    updated["notes"] = ["[2026-02-09T00:00:00+00:00] investigating root cause"]

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(),
        _fake_connection([updated])(autocommit=True),
    ]):
        resp = await client.patch(
            "/api/v1/incidents/inc-note",
            json={"note": "investigating root cause"},
        )

    assert resp.status_code == 200
    assert len(resp.json()["notes"]) >= 1


# ── PATCH — no fields → 400 ──────────────────────────────────

@pytest.mark.asyncio
async def test_patch_empty_body(client):
    row = _make_incident_row(incident_id="inc-empty")

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(),
    ]):
        resp = await client.patch("/api/v1/incidents/inc-empty", json={})
    assert resp.status_code == 400


# ── PATCH — incident not found ───────────────────────────────

@pytest.mark.asyncio
async def test_patch_not_found(client):
    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([None])(),
    ]):
        resp = await client.patch(
            "/api/v1/incidents/inc-nope",
            json={"status": "acknowledged"},
        )
    assert resp.status_code == 404


# ── GET /api/v1/incidents/{id}/metrics ───────────────────────

@pytest.mark.asyncio
async def test_get_incident_metrics_open(client):
    """Open incident has null MTTA/MTTR."""
    row = {
        "incident_id": "inc-met",
        "status": "open",
        "created_at": datetime.now(timezone.utc),
        "acknowledged_at": None,
        "resolved_at": None,
    }

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(),
    ]):
        resp = await client.get("/api/v1/incidents/inc-met/metrics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["mtta_seconds"] is None
    assert body["mttr_seconds"] is None


@pytest.mark.asyncio
async def test_get_incident_metrics_resolved(client):
    """Resolved incident has MTTA + MTTR."""
    now = datetime.now(timezone.utc)
    row = {
        "incident_id": "inc-met2",
        "status": "resolved",
        "created_at": now - timedelta(minutes=30),
        "acknowledged_at": now - timedelta(minutes=28),
        "resolved_at": now,
    }

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([row])(),
    ]):
        resp = await client.get("/api/v1/incidents/inc-met2/metrics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["mtta_seconds"] == pytest.approx(120.0, abs=1.0)
    assert body["mttr_seconds"] == pytest.approx(1800.0, abs=1.0)


@pytest.mark.asyncio
async def test_get_incident_metrics_not_found(client):
    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([None])(),
    ]):
        resp = await client.get("/api/v1/incidents/inc-nope/metrics")
    assert resp.status_code == 404


# ── GET /api/v1/incidents/analytics ──────────────────────────

@pytest.mark.asyncio
async def test_get_analytics(client):
    summary = {
        "total": 10,
        "open_count": 3,
        "ack_count": 2,
        "resolved_count": 5,
        "avg_mtta": 120.5,
        "avg_mttr": 3600.0,
    }
    sev_rows = [{"severity": "critical", "cnt": 4}, {"severity": "low", "cnt": 6}]
    svc_rows = [{"service": "web", "cnt": 7}, {"service": "api", "cnt": 3}]

    # Analytics uses ONE connection + ONE cursor with 3 sequential execute/fetch calls.
    fetch_one_results = iter([summary])
    fetch_all_results = iter([sev_rows, svc_rows])

    @contextmanager
    def _analytics_conn(autocommit=False):
        cur = MagicMock()
        cur.fetchone = MagicMock(side_effect=lambda: next(fetch_one_results))
        cur.fetchall = MagicMock(side_effect=lambda: next(fetch_all_results))

        conn = MagicMock()
        conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
        conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        yield conn

    with patch("app.routers.api.get_db_connection", side_effect=[_analytics_conn()]):
        resp = await client.get("/api/v1/incidents/analytics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_incidents"] == 10
    assert body["avg_mtta_seconds"] == 120.5
    assert body["by_severity"]["critical"] == 4
    assert body["by_service"]["web"] == 7
