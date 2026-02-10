"""Dedicated tests for MTTA / MTTR calculation logic.

Validates:
- MTTA = acknowledged_at - created_at
- MTTR = resolved_at - created_at
- Not-yet-acknowledged → MTTA is None
- Not-yet-resolved → MTTR is None
- Prometheus histogram observation on acknowledge / resolve
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from helpers import fake_connection as _fake_connection


def _incident_row(
    incident_id="inc-mtta",
    severity="high",
    status="open",
    created_at=None,
    acknowledged_at=None,
    resolved_at=None,
):
    now = datetime.now(timezone.utc)
    return {
        "id": uuid.uuid4(),
        "incident_id": incident_id,
        "title": "Test",
        "description": None,
        "service": "test-svc",
        "severity": severity,
        "status": status,
        "assigned_to": None,
        "notes": "[]",
        "created_at": created_at or (now - timedelta(minutes=10)),
        "acknowledged_at": acknowledged_at,
        "resolved_at": resolved_at,
        "updated_at": now,
    }


# ── MTTA on acknowledge ─────────────────────────────────────


@pytest.mark.asyncio
async def test_mtta_calculated_on_acknowledge(client):
    """Acknowledging an open incident should observe MTTA in the histogram."""
    now = datetime.now(timezone.utc)
    created = now - timedelta(minutes=2)
    row = _incident_row(status="open", created_at=created)
    updated = _incident_row(status="acknowledged", created_at=created, acknowledged_at=now)

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(),
            _fake_connection([updated])(autocommit=True),
        ],
    ):
        with patch("app.routers.api.incident_mtta_seconds") as mock_mtta:
            resp = await client.patch(
                "/api/v1/incidents/inc-mtta",
                json={"status": "acknowledged"},
            )
            # MTTA histogram should have been observed
            mock_mtta.labels.assert_called_with(severity="high")
            mock_mtta.labels(severity="high").observe.assert_called_once()
            observed_val = mock_mtta.labels(severity="high").observe.call_args[0][0]
            assert 110 <= observed_val <= 130  # ~120s (2 minutes)

    assert resp.status_code == 200


# ── MTTR on resolve ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_mttr_calculated_on_resolve(client):
    """Resolving an incident should observe MTTR in the histogram."""
    now = datetime.now(timezone.utc)
    created = now - timedelta(minutes=30)
    ack = now - timedelta(minutes=28)
    row = _incident_row(status="acknowledged", created_at=created, acknowledged_at=ack)
    updated = _incident_row(status="resolved", created_at=created, acknowledged_at=ack, resolved_at=now)

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(),
            _fake_connection([updated])(autocommit=True),
        ],
    ):
        with patch("app.routers.api.incident_mttr_seconds") as mock_mttr:
            resp = await client.patch(
                "/api/v1/incidents/inc-mtta",
                json={"status": "resolved"},
            )
            mock_mttr.labels.assert_called_with(severity="high")
            mock_mttr.labels(severity="high").observe.assert_called_once()
            observed_val = mock_mttr.labels(severity="high").observe.call_args[0][0]
            assert 1790 <= observed_val <= 1810  # ~1800s (30 minutes)

    assert resp.status_code == 200


# ── No MTTA when already acknowledged ────────────────────────


@pytest.mark.asyncio
async def test_no_duplicate_mtta(client):
    """Re-acknowledging should NOT re-observe MTTA."""
    now = datetime.now(timezone.utc)
    created = now - timedelta(minutes=10)
    ack = now - timedelta(minutes=8)
    row = _incident_row(status="acknowledged", created_at=created, acknowledged_at=ack)
    updated = _incident_row(status="acknowledged", created_at=created, acknowledged_at=ack)

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(),
            _fake_connection([updated])(autocommit=True),
        ],
    ):
        with patch("app.routers.api.incident_mtta_seconds") as mock_mtta:
            resp = await client.patch(
                "/api/v1/incidents/inc-mtta",
                json={"status": "acknowledged"},
            )
            # MTTA should NOT be observed because acknowledged_at is already set
            mock_mtta.labels(severity="high").observe.assert_not_called()

    assert resp.status_code == 200


# ── Metrics endpoint: not yet acknowledged ───────────────────


@pytest.mark.asyncio
async def test_metrics_endpoint_no_ack(client):
    row = {
        "incident_id": "inc-noack",
        "status": "open",
        "created_at": datetime.now(timezone.utc),
        "acknowledged_at": None,
        "resolved_at": None,
    }
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(),
        ],
    ):
        resp = await client.get("/api/v1/incidents/inc-noack/metrics")

    assert resp.status_code == 200
    assert resp.json()["mtta_seconds"] is None
    assert resp.json()["mttr_seconds"] is None


# ── Metrics endpoint: acknowledged but not resolved ──────────


@pytest.mark.asyncio
async def test_metrics_endpoint_ack_no_resolve(client):
    now = datetime.now(timezone.utc)
    row = {
        "incident_id": "inc-ackonly",
        "status": "acknowledged",
        "created_at": now - timedelta(minutes=5),
        "acknowledged_at": now - timedelta(minutes=3),
        "resolved_at": None,
    }
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(),
        ],
    ):
        resp = await client.get("/api/v1/incidents/inc-ackonly/metrics")

    assert resp.status_code == 200
    body = resp.json()
    assert body["mtta_seconds"] == pytest.approx(120.0, abs=1.0)
    assert body["mttr_seconds"] is None


# ── Open incidents gauge decremented on resolve ──────────────


@pytest.mark.asyncio
async def test_open_gauge_decremented_on_resolve(client):
    now = datetime.now(timezone.utc)
    row = _incident_row(status="acknowledged", acknowledged_at=now - timedelta(minutes=1))
    updated = _incident_row(status="resolved", acknowledged_at=now - timedelta(minutes=1), resolved_at=now)

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(),
            _fake_connection([updated])(autocommit=True),
        ],
    ):
        with patch("app.routers.api.open_incidents") as mock_gauge:
            resp = await client.patch(
                "/api/v1/incidents/inc-mtta",
                json={"status": "resolved"},
            )
            mock_gauge.labels.assert_called_with(severity="high")
            mock_gauge.labels(severity="high").dec.assert_called_once()

    assert resp.status_code == 200
