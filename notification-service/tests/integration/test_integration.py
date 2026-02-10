"""Integration tests for notification-service.

These tests run against a REAL PostgreSQL database and the live ASGI app.
They require:
  - DATABASE_URL env var pointing to a running PostgreSQL instance
  - The database initialised with 01-init-database.sql

Run with:
    pytest tests/integration/ -v -m integration
"""

import os
import uuid

import psycopg2
import pytest
from httpx import ASGITransport, AsyncClient

# Skip the entire module if no real database is available
DATABASE_URL = os.getenv("DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL not set -- skip integration tests"),
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
async def test_post_notification_stores_in_database(live_client, db_conn):
    """POST /api/v1/notify stores a notification in notifications.notifications."""
    payload = {
        "incident_id": f"inc-{uuid.uuid4().hex[:8]}",
        "engineer": f"integ-{uuid.uuid4().hex[:6]}@example.com",
        "message": "Integration test notification",
        "channel": "mock",
    }

    resp = await live_client.post("/api/v1/notify", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    notification_id = body["notification_id"]
    assert notification_id.startswith("notif-")

    # Verify in database
    cur = db_conn.cursor()
    cur.execute(
        "SELECT engineer, channel, status FROM notifications.notifications WHERE notification_id = %s",
        (notification_id,),
    )
    row = cur.fetchone()
    cur.close()

    assert row is not None
    assert row[0] == payload["engineer"]
    assert row[1] == "mock"
    assert row[2] == "delivered"


@pytest.mark.asyncio
async def test_get_notification_by_id(live_client):
    """POST then GET the same notification by ID."""
    payload = {
        "incident_id": f"inc-{uuid.uuid4().hex[:8]}",
        "engineer": f"integ-get-{uuid.uuid4().hex[:6]}@example.com",
        "message": "GET by ID integration test",
        "channel": "mock",
    }

    post_resp = await live_client.post("/api/v1/notify", json=payload)
    notification_id = post_resp.json()["notification_id"]

    get_resp = await live_client.get(f"/api/v1/notifications/{notification_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["notification_id"] == notification_id


@pytest.mark.asyncio
async def test_list_notifications(live_client):
    """POST a notification then verify it appears in the list."""
    engineer = f"integ-list-{uuid.uuid4().hex[:6]}@example.com"
    payload = {
        "incident_id": f"inc-{uuid.uuid4().hex[:8]}",
        "engineer": engineer,
        "message": "List integration test",
        "channel": "mock",
    }

    await live_client.post("/api/v1/notify", json=payload)

    resp = await live_client.get("/api/v1/notifications")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_list_notifications_filter_by_channel(live_client):
    """POST a mock notification and filter list by channel=mock."""
    payload = {
        "incident_id": f"inc-{uuid.uuid4().hex[:8]}",
        "engineer": f"integ-chan-{uuid.uuid4().hex[:6]}@example.com",
        "message": "Channel filter test",
        "channel": "mock",
    }

    await live_client.post("/api/v1/notify", json=payload)

    resp = await live_client.get("/api/v1/notifications?channel=mock")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1


@pytest.mark.asyncio
async def test_get_nonexistent_notification_returns_404(live_client):
    """GET with a bogus notification_id returns 404."""
    resp = await live_client.get("/api/v1/notifications/notif-does-not-exist")
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
    assert "oncall_notifications_sent_total" in text
    assert "http_requests_total" in text or "http_request" in text


@pytest.mark.asyncio
async def test_post_notification_validation_error(live_client):
    """Missing required fields returns 422."""
    resp = await live_client.post("/api/v1/notify", json={"engineer": "x"})
    assert resp.status_code == 422
