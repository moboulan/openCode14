"""Integration tests for alert-ingestion-service.

These tests run against a REAL PostgreSQL database and the live ASGI app.
They require:
  - DATABASE_URL env var pointing to a running PostgreSQL instance
  - The database initialised with 01-init-database.sql

Run with:
    pytest tests/integration/ -v -m integration

In CI (GitHub Actions Stage 5), the postgres service container is started
automatically and the DB is seeded before these tests execute.
"""

import os
import uuid
from datetime import datetime, timezone

import psycopg2
import pytest
from httpx import ASGITransport, AsyncClient

# Skip the entire module if no real database is available
DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL not set — skip integration tests"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_conn():
    """Raw psycopg2 connection for verification queries."""
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    yield conn
    conn.close()


@pytest.fixture()
async def live_client():
    """Async client wired to the real FastAPI app (no DB mocks)."""
    from app.main import app

    transport = ASGITransport(app=app)  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_alert_stores_in_database(live_client, db_conn):
    """POST /api/v1/alerts stores the alert in alerts.alerts."""
    payload = {
        "service": f"integ-svc-{uuid.uuid4().hex[:6]}",
        "severity": "low",
        "message": "Integration test alert",
        "labels": {"env": "ci"},
    }

    resp = await live_client.post("/api/v1/alerts", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    alert_id = body["alert_id"]
    assert alert_id.startswith("alert-")

    # Verify in database
    cur = db_conn.cursor()
    cur.execute("SELECT service, severity, message FROM alerts.alerts WHERE alert_id = %s", (alert_id,))
    row = cur.fetchone()
    cur.close()

    assert row is not None
    assert row[0] == payload["service"]
    assert row[1] == "low"
    assert row[2] == payload["message"]


@pytest.mark.asyncio
async def test_get_alert_by_id(live_client, db_conn):
    """POST then GET the same alert by ID."""
    payload = {
        "service": f"integ-get-{uuid.uuid4().hex[:6]}",
        "severity": "medium",
        "message": "GET by ID integration test",
    }

    post_resp = await live_client.post("/api/v1/alerts", json=payload)
    alert_id = post_resp.json()["alert_id"]

    get_resp = await live_client.get(f"/api/v1/alerts/{alert_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["alert_id"] == alert_id
    assert get_resp.json()["service"] == payload["service"]


@pytest.mark.asyncio
async def test_list_alerts_filter_by_service(live_client):
    """POST two alerts with different services, filter list by one service."""
    svc_a = f"integ-list-a-{uuid.uuid4().hex[:6]}"
    svc_b = f"integ-list-b-{uuid.uuid4().hex[:6]}"

    await live_client.post("/api/v1/alerts", json={"service": svc_a, "severity": "low", "message": "A"})
    await live_client.post("/api/v1/alerts", json={"service": svc_b, "severity": "low", "message": "B"})

    resp = await live_client.get(f"/api/v1/alerts?service={svc_a}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert all(a["service"] == svc_a for a in body["alerts"])


@pytest.mark.asyncio
async def test_list_alerts_filter_by_severity(live_client):
    """Filter alerts by severity level."""
    svc = f"integ-sev-{uuid.uuid4().hex[:6]}"

    await live_client.post("/api/v1/alerts", json={"service": svc, "severity": "critical", "message": "Crit"})
    await live_client.post("/api/v1/alerts", json={"service": svc, "severity": "low", "message": "Low"})

    resp = await live_client.get(f"/api/v1/alerts?service={svc}&severity=critical")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert all(a["severity"] == "critical" for a in body["alerts"])


@pytest.mark.asyncio
async def test_get_nonexistent_alert_returns_404(live_client):
    """GET with a bogus alert_id returns 404."""
    resp = await live_client.get("/api/v1/alerts/alert-does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint_with_real_db(live_client):
    """Health endpoint reports healthy when DB is reachable."""
    resp = await live_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["checks"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_with_real_db(live_client):
    """Readiness probe returns ready when DB is up."""
    resp = await live_client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_liveness(live_client):
    """Liveness probe always returns alive."""
    resp = await live_client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_metrics_endpoint(live_client):
    """The /metrics endpoint returns Prometheus text format."""
    resp = await live_client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "alerts_received_total" in text
    assert "alerts_correlated_total" in text
    assert "http_requests_total" in text or "http_request" in text


@pytest.mark.asyncio
async def test_post_alert_validation_error(live_client):
    """Missing required fields returns 422."""
    resp = await live_client.post("/api/v1/alerts", json={"service": "x"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_correlation_two_alerts_same_service_severity(live_client, db_conn):
    """Two alerts with same service+severity within the correlation window
    should ideally correlate to the same incident (if incident service is running).
    If incident service is down, both still get stored with null incident_id.
    This test verifies both alerts are stored regardless."""
    svc = f"integ-corr-{uuid.uuid4().hex[:6]}"

    resp1 = await live_client.post(
        "/api/v1/alerts", json={"service": svc, "severity": "high", "message": "Correlation test 1"}
    )
    resp2 = await live_client.post(
        "/api/v1/alerts", json={"service": svc, "severity": "high", "message": "Correlation test 2"}
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201

    # Both alerts exist in DB
    cur = db_conn.cursor()
    cur.execute("SELECT COUNT(*) FROM alerts.alerts WHERE service = %s", (svc,))
    count = cur.fetchone()[0]
    cur.close()
    assert count == 2
