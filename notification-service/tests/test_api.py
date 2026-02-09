"""Tests for the notification API — POST /notify, GET /notifications.

All database calls are mocked so these run without PostgreSQL.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from helpers import fake_connection as _fake_connection


def _make_notification_row(
    notification_id="notif-test123",
    incident_id="inc-test123",
    engineer="alice@example.com",
    channel="mock",
    status="delivered",
    message="Test notification",
):
    """Build a dict mimicking a DB row from notifications.notifications."""
    return {
        "id": uuid.uuid4(),
        "notification_id": notification_id,
        "incident_id": incident_id,
        "engineer": engineer,
        "channel": channel,
        "status": status,
        "message": message,
        "created_at": datetime.now(timezone.utc),
    }


# ── POST /api/v1/notify ─────────────────────────────────────


@pytest.mark.asyncio
async def test_send_mock_notification(client, sample_notification_payload):
    """Sending a mock notification stores it and returns 201."""
    row = _make_notification_row()

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(autocommit=True),  # INSERT
        ],
    ):
        resp = await client.post("/api/v1/notify", json=sample_notification_payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["channel"] == "mock"
    assert body["status"] == "delivered"
    assert body["incident_id"] == "inc-test123"
    assert body["engineer"] == "alice@example.com"
    assert "notification_id" in body
    assert "timestamp" in body


@pytest.mark.asyncio
async def test_send_notification_validation_error(client):
    """Missing required fields returns 422."""
    resp = await client.post("/api/v1/notify", json={"incident_id": "x"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_send_notification_invalid_channel(client):
    """Invalid channel returns 422."""
    resp = await client.post(
        "/api/v1/notify",
        json={
            "incident_id": "inc-test",
            "engineer": "bob@example.com",
            "channel": "INVALID",
            "message": "test",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_send_email_notification_falls_back_to_mock(client):
    """Email without SENDGRID_API_KEY falls back to mock delivery."""
    row = _make_notification_row(channel="email")

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(autocommit=True),
        ],
    ):
        with patch("app.routers.api.settings") as mock_settings:
            mock_settings.SENDGRID_API_KEY = None
            mock_settings.HTTP_CLIENT_TIMEOUT = 10.0
            mock_settings.SENDGRID_FROM_EMAIL = "noreply@test.local"
            mock_settings.webhook_url_list = []
            resp = await client.post(
                "/api/v1/notify",
                json={
                    "incident_id": "inc-email",
                    "engineer": "alice@example.com",
                    "channel": "email",
                    "message": "Email test",
                },
            )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "delivered"


@pytest.mark.asyncio
async def test_send_webhook_no_urls_configured(client):
    """Webhook with no URLs configured returns failed status."""
    row = _make_notification_row(channel="webhook", status="failed")

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(autocommit=True),
        ],
    ):
        with patch("app.routers.api.settings") as mock_settings:
            mock_settings.webhook_url_list = []
            mock_settings.HTTP_CLIENT_TIMEOUT = 10.0
            resp = await client.post(
                "/api/v1/notify",
                json={
                    "incident_id": "inc-webhook",
                    "engineer": "bob@example.com",
                    "channel": "webhook",
                    "message": "Webhook test",
                },
            )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "failed"


@pytest.mark.asyncio
async def test_send_notification_db_failure_still_returns_201(client):
    """If DB storage fails, notification is still sent and returns 201."""
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=Exception("DB down"),
    ):
        resp = await client.post(
            "/api/v1/notify",
            json={
                "incident_id": "inc-dbfail",
                "engineer": "charlie@example.com",
                "channel": "mock",
                "message": "DB failure test",
            },
        )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "delivered"


# ── GET /api/v1/notifications ────────────────────────────────


def _list_connection(total: int, rows: list):
    """Return a get_db_connection CM whose cursor serves COUNT then SELECT."""
    from contextlib import contextmanager

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
async def test_list_notifications(client):
    """GET /notifications returns paginated list."""
    rows = [_make_notification_row()]

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _list_connection(total=1, rows=rows)(),
        ],
    ):
        resp = await client.get("/api/v1/notifications")

    assert resp.status_code == 200
    body = resp.json()
    assert "notifications" in body
    assert body["total"] == 1
    assert "limit" in body
    assert "offset" in body


@pytest.mark.asyncio
async def test_list_notifications_with_filters(client):
    """GET /notifications with filters returns filtered results."""
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _list_connection(total=0, rows=[])(),
        ],
    ):
        resp = await client.get("/api/v1/notifications?incident_id=inc-test&channel=mock")

    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_list_notifications_empty(client):
    """Empty notification list returns correctly."""
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _list_connection(total=0, rows=[])(),
        ],
    ):
        resp = await client.get("/api/v1/notifications")

    assert resp.status_code == 200
    body = resp.json()
    assert body["notifications"] == []
    assert body["total"] == 0


# ── GET /api/v1/notifications/{notification_id} ──────────────


@pytest.mark.asyncio
async def test_get_notification_found(client):
    """GET /notifications/{id} returns the notification."""
    row = _make_notification_row(notification_id="notif-found")

    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([row])(),
        ],
    ):
        resp = await client.get("/api/v1/notifications/notif-found")

    assert resp.status_code == 200
    body = resp.json()
    assert body["notification_id"] == "notif-found"


@pytest.mark.asyncio
async def test_get_notification_not_found(client):
    """GET /notifications/{id} returns 404 when not found."""
    with patch(
        "app.routers.api.get_db_connection",
        side_effect=[
            _fake_connection([None])(),
        ],
    ):
        resp = await client.get("/api/v1/notifications/notif-nope")

    assert resp.status_code == 404
