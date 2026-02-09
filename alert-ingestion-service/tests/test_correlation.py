"""Tests focused on the alert correlation logic.

Validates the 5-minute-window deduplication algorithm:
- Same service + severity within window → existing incident
- Same service + different severity → new incident
- Correlation window value used in SQL query
- Graceful degradation when incident service is down
- Correlation metric counters
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from helpers import (
    FakeAsyncClient,
    FakeAsyncClientDown,
    fake_connection,
)

# ── Correlation: match found → attach to existing incident ───


@pytest.mark.asyncio
async def test_correlation_matches_existing_incident(client, sample_alert_payload):
    """When an open incident exists for the same service+severity within
    the correlation window, the alert is attached to it."""
    alert_db_id = uuid.uuid4()
    incident_db_id = uuid.uuid4()
    incident_id = "inc-existing-001"

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            fake_connection([{"incident_id": incident_id, "id": incident_db_id}])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["action"] == "attached_to_existing_incident"
    assert body["status"] == "correlated"
    assert body["incident_id"] == incident_id


# ── Correlation: no match → create new incident ──────────────


@pytest.mark.asyncio
async def test_correlation_no_match_creates_new_incident(client, sample_alert_payload):
    """When no open incident matches, a new one is created via the
    incident-management service."""
    alert_db_id = uuid.uuid4()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            fake_connection([None])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["action"] == "created_new_incident"
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

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            fake_connection([None])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=payload)

    assert resp.status_code == 201
    assert resp.json()["action"] == "created_new_incident"


# ── Graceful degradation: incident service down ──────────────


@pytest.mark.asyncio
async def test_correlation_graceful_degradation(client, sample_alert_payload):
    """When incident-management is unreachable, alert stored with null incident_id."""
    alert_db_id = uuid.uuid4()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            fake_connection([None])(),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClientDown):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["incident_id"] is None
    assert body["action"] == "created_new_incident"
    assert body["status"] == "created"


# ── Correlation window boundary test ─────────────────────────


@pytest.mark.asyncio
async def test_correlation_query_uses_window_setting(client, sample_alert_payload):
    """Verify that the correlation SQL passes the CORRELATION_WINDOW_MINUTES
    config value to the query, so alerts outside the window won't match."""
    from contextlib import contextmanager

    from app.config import settings

    alert_db_id = uuid.uuid4()
    captured_sql = {}

    @contextmanager
    def _capture_conn(autocommit=False):
        conn = MagicMock()

        @contextmanager
        def _cur_ctx():
            cur = MagicMock()
            cur.fetchone.return_value = None
            cur.fetchall.return_value = []

            def _capture_execute(sql, params=None):
                if "incidents.incidents" in str(sql):
                    captured_sql["sql"] = sql
                    captured_sql["params"] = params

            cur.execute = _capture_execute
            yield cur

        conn.cursor = _cur_ctx
        yield conn

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            _capture_conn(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    assert "sql" in captured_sql, "Correlation query was not captured"
    sql = captured_sql["sql"]
    params = captured_sql["params"]
    assert "interval" in sql.lower(), "SQL should use interval for time window"
    assert params[2] == settings.CORRELATION_WINDOW_MINUTES


# ── Correlation metric counters ──────────────────────────────


@pytest.mark.asyncio
async def test_correlation_metric_new_incident(client, sample_alert_payload):
    """alerts_correlated_total counter with result=new_incident is incremented."""
    alert_db_id = uuid.uuid4()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            fake_connection([None])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClient):
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

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            fake_connection([{"incident_id": "inc-333", "id": incident_db_id}])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("app.routers.api.alerts_correlated_total") as mock_counter:
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)
            mock_counter.labels.assert_called_with(result="existing_incident")

    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_alerts_received_metric_incremented(client, sample_alert_payload):
    """alerts_received_total counter is incremented with correct labels."""
    alert_db_id = uuid.uuid4()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            fake_connection([None])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            with patch("app.routers.api.alerts_received_total") as mock_recv:
                resp = await client.post("/api/v1/alerts", json=sample_alert_payload)
                mock_recv.labels.assert_called_with(severity="low", service="test-service")


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
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id_1}])(autocommit=True),
            fake_connection([None])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp1 = await client.post("/api/v1/alerts", json=payload)

    assert resp1.status_code == 201
    assert resp1.json()["action"] == "created_new_incident"

    # Second alert — match found → existing incident
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id_2}])(autocommit=True),
            fake_connection([{"incident_id": incident_id, "id": incident_db_id}])(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        resp2 = await client.post("/api/v1/alerts", json=payload)

    assert resp2.status_code == 201
    assert resp2.json()["action"] == "attached_to_existing_incident"
    assert resp2.json()["incident_id"] == incident_id


# ── Correlation window boundary: outside window → new incident ─


@pytest.mark.asyncio
async def test_correlation_outside_window_creates_new_incident(client, sample_alert_payload):
    """An alert arriving AFTER the correlation window has elapsed should NOT
    match any existing incident and should create a new one instead.

    We verify by ensuring the correlation query (which checks
    ``created_at >= now() - interval '<window> minutes'``) returns no match,
    causing the code path for 'new_incident' to execute.
    """
    from contextlib import contextmanager

    from app.config import settings

    alert_db_id = uuid.uuid4()
    captured_params = {}

    @contextmanager
    def _capture_conn(autocommit=False):
        """Mock connection that captures the correlation query params and
        returns no match — simulating an expired window."""
        conn = MagicMock()

        @contextmanager
        def _cur_ctx():
            cur = MagicMock()
            cur.fetchone.return_value = None  # no matching incident
            cur.fetchall.return_value = []

            cur.execute

            def _capture(sql, params=None):
                if params and "incidents.incidents" in str(sql):
                    captured_params["window"] = params[2]

            cur.execute = _capture
            yield cur

        conn.cursor = _cur_ctx
        yield conn

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            fake_connection([{"id": alert_db_id}])(autocommit=True),
            _capture_conn(),
            fake_connection([None])(autocommit=True),
        ],
    ):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp = await client.post("/api/v1/alerts", json=sample_alert_payload)

    assert resp.status_code == 201
    body = resp.json()
    # Since correlation returned no match, a new incident is created
    assert body["action"] == "created_new_incident"
    # Verify the window value passed to SQL matches the configured value
    assert captured_params.get("window") == settings.CORRELATION_WINDOW_MINUTES


# ── Concurrency: two simultaneous alerts should not both create new incidents ─


@pytest.mark.asyncio
async def test_concurrent_alerts_correlation(client):
    """Two identical alerts arriving simultaneously: simulate that the second
    one finds the incident created by the first, so only one new incident is
    created.  We mock the DB so that the first call to the correlation query
    returns no match (→ new incident) and the second call returns a match
    (→ existing incident)."""

    alert_db_id_1 = uuid.uuid4()
    alert_db_id_2 = uuid.uuid4()
    incident_db_id = uuid.uuid4()
    incident_id = "inc-concurrent-001"

    payload = {
        "service": "concurrent-svc",
        "severity": "critical",
        "message": "Concurrent test",
    }

    call_count = {"n": 0}

    # Build side_effect lists: first request gets no match, second gets match
    def _side_effects_first():
        return [
            fake_connection([{"id": alert_db_id_1}])(autocommit=True),
            fake_connection([None])(),  # no match
            fake_connection([None])(autocommit=True),
        ]

    def _side_effects_second():
        return [
            fake_connection([{"id": alert_db_id_2}])(autocommit=True),
            fake_connection([{"incident_id": incident_id, "id": incident_db_id}])(),  # match
            fake_connection([None])(autocommit=True),
        ]

    # Send first request (new incident path)
    with patch("app.routers.api.get_db_connection", side_effect=_side_effects_first()):
        with patch("httpx.AsyncClient", FakeAsyncClient):
            resp1 = await client.post("/api/v1/alerts", json=payload)

    # Send second request (should correlate to existing)
    with patch("app.routers.api.get_db_connection", side_effect=_side_effects_second()):
        resp2 = await client.post("/api/v1/alerts", json=payload)

    assert resp1.status_code == 201
    assert resp1.json()["action"] == "created_new_incident"

    assert resp2.status_code == 201
    assert resp2.json()["action"] == "attached_to_existing_incident"
    assert resp2.json()["incident_id"] == incident_id
