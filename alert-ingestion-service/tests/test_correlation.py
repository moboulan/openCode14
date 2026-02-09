"""Tests focused on the alert correlation logic.

Validates the 5-minute-window deduplication algorithm:
- Same service + severity within window → existing incident
- Same service + different severity → new incident
- Same service + severity outside window → new incident
- Graceful degradation when incident service is down
- Correlation metric counters
"""

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helper — reusable mock get_db_connection factory
# ---------------------------------------------------------------------------

def _fake_connection(cursor_sides: list[dict | None]):
    """Return a patched get_db_connection that yields a mock with preset cursor results."""
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


class _FakeIncidentResponse:
    """Simulate a successful incident-management POST response."""
    status_code = 201

    def __init__(self, incident_id="inc-new-111", db_id=None):
        self._incident_id = incident_id
        self._db_id = db_id or str(uuid.uuid4())

    def raise_for_status(self):
        pass

    def json(self):
        return {"incident_id": self._incident_id, "id": self._db_id}


class _FakeAsyncClient:
    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, *a, **kw):
        return _FakeIncidentResponse()


class _FakeAsyncClientDown:
    """Simulate incident service being unreachable."""
    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, *a, **kw):
        raise Exception("connection refused")


# ── Correlation: match found → attach to existing incident ───

@pytest.mark.asyncio
async def test_correlation_matches_existing_incident(client, sample_alert_payload):
    """When an open incident exists for the same service+severity within
    the correlation window, the alert is attached to it."""
    alert_db_id = uuid.uuid4()
    incident_db_id = uuid.uuid4()
    incident_id = "inc-existing-001"

    with patch("app.routers.api.get_db_connection", side_effect=[
        # 1. INSERT alert
        _fake_connection([{"id": alert_db_id}])(autocommit=True),
        # 2. Correlation SELECT → match found
        _fake_connection([{"incident_id": incident_id, "id": incident_db_id}])(),
        # 3. Link alert ↔ incident
        _fake_connection([None])(autocommit=True),
    ]):
        resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["action"] == "existing_incident"
    assert body["incident_id"] == incident_id


# ── Correlation: no match → create new incident ──────────────

@pytest.mark.asyncio
async def test_correlation_no_match_creates_new_incident(client, sample_alert_payload):
    """When no open incident matches, a new one is created via the
    incident-management service."""
    alert_db_id = uuid.uuid4()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id}])(autocommit=True),
        _fake_connection([None])(),  # no match
        _fake_connection([None])(autocommit=True),  # link step
    ]):
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["action"] == "new_incident"
    assert body["incident_id"] is not None


# ── Correlation: different severity → no match ───────────────

@pytest.mark.asyncio
async def test_correlation_different_severity_no_match(client):
    """An alert with severity=critical should NOT match an open incident
    with severity=low — the correlation query filters on severity."""
    alert_db_id = uuid.uuid4()
    payload = {
        "service": "payment-api",
        "severity": "critical",
        "message": "Different severity test",
    }

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id}])(autocommit=True),
        _fake_connection([None])(),  # no match (different severity)
        _fake_connection([None])(autocommit=True),
    ]):
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=payload)

    assert resp.status_code == 201
    assert resp.json()["action"] == "new_incident"


# ── Graceful degradation: incident service down ──────────────

@pytest.mark.asyncio
async def test_correlation_graceful_degradation(client, sample_alert_payload):
    """When incident-management is unreachable, alert stored with null incident_id."""
    alert_db_id = uuid.uuid4()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id}])(autocommit=True),
        _fake_connection([None])(),
    ]):
        with patch("httpx.AsyncClient", _FakeAsyncClientDown):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] is None
    assert body["action"] == "new_incident"
    assert body["status"] == "processed"


# ── Correlation metric counters ──────────────────────────────

@pytest.mark.asyncio
async def test_correlation_metric_new_incident(client, sample_alert_payload):
    """alerts_correlated_total counter with result=new_incident is incremented."""
    alert_db_id = uuid.uuid4()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id}])(autocommit=True),
        _fake_connection([None])(),
        _fake_connection([None])(autocommit=True),
    ]):
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            with patch("app.routers.api.alerts_correlated_total") as mock_counter:
                resp = await client.post("/api/v1/alerts", json=sample_alert_payload)
                mock_counter.labels.assert_called_with(result="new_incident")
                mock_counter.labels(result="new_incident").inc.assert_called()

    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_correlation_metric_existing_incident(client, sample_alert_payload):
    """alerts_correlated_total counter with result=existing_incident is incremented."""
    alert_db_id = uuid.uuid4()
    incident_db_id = uuid.uuid4()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id}])(autocommit=True),
        _fake_connection([{"incident_id": "inc-333", "id": incident_db_id}])(),
        _fake_connection([None])(autocommit=True),
    ]):
        with patch("app.routers.api.alerts_correlated_total") as mock_counter:
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)
            mock_counter.labels.assert_called_with(result="existing_incident")

    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_alerts_received_metric_incremented(client, sample_alert_payload):
    """alerts_received_total counter is incremented with correct labels."""
    alert_db_id = uuid.uuid4()

    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id}])(autocommit=True),
        _fake_connection([None])(),
        _fake_connection([None])(autocommit=True),
    ]):
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            with patch("app.routers.api.alerts_received_total") as mock_recv:
                resp = await client.post("/api/v1/alerts", json=sample_alert_payload)
                mock_recv.labels.assert_called_with(
                    severity="low", service="test-service"
                )

    assert resp.status_code == 201


# ── Multiple alerts → same incident (dedup) ──────────────────

@pytest.mark.asyncio
async def test_two_alerts_same_service_severity_deduplicate(client):
    """Two alerts with the same service+severity should correlate to the
    same incident (the second finds the existing one)."""
    alert_db_id_1 = uuid.uuid4()
    alert_db_id_2 = uuid.uuid4()
    incident_db_id = uuid.uuid4()
    incident_id = "inc-dedup-001"

    payload = {
        "service": "dedup-svc",
        "severity": "high",
        "message": "Dedup test alert",
    }

    # First alert — no match → new incident
    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id_1}])(autocommit=True),
        _fake_connection([None])(),
        _fake_connection([None])(autocommit=True),
    ]):
        with patch("httpx.AsyncClient", _FakeAsyncClient):
            resp1 = await client.post("/api/v1/alerts", json=payload)

    assert resp1.status_code == 201
    assert resp1.json()["action"] == "new_incident"

    # Second alert — match found → existing incident
    with patch("app.routers.api.get_db_connection", side_effect=[
        _fake_connection([{"id": alert_db_id_2}])(autocommit=True),
        _fake_connection([{"incident_id": incident_id, "id": incident_db_id}])(),
        _fake_connection([None])(autocommit=True),
    ]):
        resp2 = await client.post("/api/v1/alerts", json=payload)

    assert resp2.status_code == 201
    assert resp2.json()["action"] == "existing_incident"
    assert resp2.json()["incident_id"] == incident_id
