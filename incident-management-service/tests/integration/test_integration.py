"""Integration tests for incident-management-service.

These tests run against a REAL PostgreSQL database and the live ASGI app.
They require:
  - DATABASE_URL env var pointing to a running PostgreSQL instance
  - The database initialised with 01-init-database.sql

Run with:
    pytest tests/integration/ -v -m integration
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_incident(live_client, db_conn):
    """POST /api/v1/incidents stores the incident in incidents.incidents."""
    payload = {
        "title": f"[LOW] integ-svc-{uuid.uuid4().hex[:6]}: CI test",
        "service": f"integ-svc-{uuid.uuid4().hex[:6]}",
        "severity": "low",
        "description": "Integration test incident",
    }

    resp = await live_client.post("/api/v1/incidents", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    incident_id = body["incident_id"]
    assert incident_id.startswith("inc-")

    # Verify in database
    cur = db_conn.cursor()
    cur.execute(
        "SELECT service, severity, status FROM incidents.incidents WHERE incident_id = %s",
        (incident_id,),
    )
    row = cur.fetchone()
    cur.close()

    assert row is not None
    assert row[0] == payload["service"]
    assert row[1] == "low"
    assert row[2] == "open"


@pytest.mark.asyncio
async def test_get_incident_by_id(live_client):
    """POST then GET the same incident by ID."""
    svc = f"integ-get-{uuid.uuid4().hex[:6]}"
    payload = {
        "title": f"[MEDIUM] {svc}: GET test",
        "service": svc,
        "severity": "medium",
    }

    post_resp = await live_client.post("/api/v1/incidents", json=payload)
    incident_id = post_resp.json()["incident_id"]

    get_resp = await live_client.get(f"/api/v1/incidents/{incident_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["incident_id"] == incident_id
    assert get_resp.json()["service"] == svc


@pytest.mark.asyncio
async def test_list_incidents_filter_by_service(live_client):
    svc = f"integ-list-{uuid.uuid4().hex[:6]}"
    await live_client.post("/api/v1/incidents", json={
        "title": f"[LOW] {svc}: A",
        "service": svc,
        "severity": "low",
    })

    resp = await live_client.get(f"/api/v1/incidents?service={svc}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    assert all(i["service"] == svc for i in body["incidents"])


@pytest.mark.asyncio
async def test_acknowledge_and_mtta(live_client):
    """Acknowledge an incident → check MTTA > 0."""
    svc = f"integ-ack-{uuid.uuid4().hex[:6]}"
    post_resp = await live_client.post("/api/v1/incidents", json={
        "title": f"[HIGH] {svc}: ACK test",
        "service": svc,
        "severity": "high",
    })
    incident_id = post_resp.json()["incident_id"]

    # Acknowledge
    patch_resp = await live_client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"status": "acknowledged"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "acknowledged"

    # Check MTTA
    met_resp = await live_client.get(f"/api/v1/incidents/{incident_id}/metrics")
    assert met_resp.status_code == 200
    assert met_resp.json()["mtta_seconds"] is not None
    assert met_resp.json()["mtta_seconds"] >= 0


@pytest.mark.asyncio
async def test_resolve_and_mttr(live_client):
    """Acknowledge then resolve → check MTTR > 0."""
    svc = f"integ-res-{uuid.uuid4().hex[:6]}"
    post_resp = await live_client.post("/api/v1/incidents", json={
        "title": f"[CRITICAL] {svc}: resolve test",
        "service": svc,
        "severity": "critical",
    })
    incident_id = post_resp.json()["incident_id"]

    await live_client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "acknowledged"})
    await live_client.patch(f"/api/v1/incidents/{incident_id}", json={"status": "resolved"})

    met_resp = await live_client.get(f"/api/v1/incidents/{incident_id}/metrics")
    assert met_resp.status_code == 200
    assert met_resp.json()["mttr_seconds"] is not None
    assert met_resp.json()["mttr_seconds"] >= 0


@pytest.mark.asyncio
async def test_add_note(live_client):
    svc = f"integ-note-{uuid.uuid4().hex[:6]}"
    post_resp = await live_client.post("/api/v1/incidents", json={
        "title": f"[LOW] {svc}: notes",
        "service": svc,
        "severity": "low",
    })
    incident_id = post_resp.json()["incident_id"]

    patch_resp = await live_client.patch(
        f"/api/v1/incidents/{incident_id}",
        json={"note": "investigating root cause"},
    )
    assert patch_resp.status_code == 200
    assert len(patch_resp.json()["notes"]) >= 1


@pytest.mark.asyncio
async def test_analytics_endpoint(live_client):
    resp = await live_client.get("/api/v1/incidents/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_incidents" in body
    assert "by_severity" in body


@pytest.mark.asyncio
async def test_get_nonexistent_incident_returns_404(live_client):
    resp = await live_client.get("/api/v1/incidents/inc-does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_health_endpoint_with_real_db(live_client):
    resp = await live_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["checks"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_readiness_with_real_db(live_client):
    resp = await live_client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_liveness(live_client):
    resp = await live_client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_metrics_endpoint(live_client):
    resp = await live_client.get("/metrics")
    assert resp.status_code == 200
    text = resp.text
    assert "incidents_total" in text
    assert "incident_mtta_seconds" in text or "incident_mttr_seconds" in text
