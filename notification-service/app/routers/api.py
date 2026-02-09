import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.config import settings
from app.database import get_db_connection
from app.metrics import (
    notification_delivery_seconds,
    oncall_notifications_sent_total,
)
from app.models import (
    NotificationChannel,
    NotificationListResponse,
    NotificationRequest,
    NotificationResponse,
    NotificationStatus,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Notification channel dispatchers
# ---------------------------------------------------------------------------


def _send_mock(notification_id: str, request: NotificationRequest) -> NotificationStatus:
    """Mock notification — log to stdout."""
    logger.info(
        f"[MOCK NOTIFICATION] id={notification_id} "
        f"incident={request.incident_id} "
        f"engineer={request.engineer} "
        f"message={request.message}"
    )
    return NotificationStatus.DELIVERED


async def _send_email(notification_id: str, request: NotificationRequest) -> NotificationStatus:
    """Send email via SendGrid API. Falls back to mock if no API key."""
    if not settings.SENDGRID_API_KEY:
        logger.info(f"[EMAIL FALLBACK→MOCK] No SENDGRID_API_KEY set. id={notification_id}")
        return _send_mock(notification_id, request)

    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_CLIENT_TIMEOUT) as client:
            resp = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": request.engineer}]}],
                    "from": {"email": settings.SENDGRID_FROM_EMAIL},
                    "subject": f"[Incident Platform] {request.incident_id}",
                    "content": [
                        {
                            "type": "text/plain",
                            "value": request.message,
                        }
                    ],
                },
            )
            if resp.status_code in (200, 201, 202):
                logger.info(f"[EMAIL SENT] id={notification_id} to={request.engineer}")
                return NotificationStatus.DELIVERED
            else:
                logger.error(f"[EMAIL FAILED] id={notification_id} status={resp.status_code} body={resp.text}")
                return NotificationStatus.FAILED
    except Exception as e:
        logger.error(f"[EMAIL ERROR] id={notification_id}: {e}")
        return NotificationStatus.FAILED


async def _send_webhook(notification_id: str, request: NotificationRequest) -> NotificationStatus:
    """Send notification to webhook URL(s)."""
    urls = []
    if request.webhook_url:
        urls.append(request.webhook_url)
    urls.extend(settings.webhook_url_list)

    if not urls:
        logger.warning(f"[WEBHOOK] No webhook URLs configured. id={notification_id}")
        return NotificationStatus.FAILED

    payload = {
        "notification_id": notification_id,
        "incident_id": request.incident_id,
        "engineer": request.engineer,
        "severity": request.severity.value if request.severity else None,
        "message": request.message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    delivered = False
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_CLIENT_TIMEOUT) as client:
            for url in urls:
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code < 400:
                        logger.info(f"[WEBHOOK SENT] id={notification_id} url={url} status={resp.status_code}")
                        delivered = True
                    else:
                        logger.warning(f"[WEBHOOK FAILED] id={notification_id} url={url} status={resp.status_code}")
                except Exception as e:
                    logger.error(f"[WEBHOOK ERROR] id={notification_id} url={url}: {e}")
    except Exception as e:
        logger.error(f"[WEBHOOK CLIENT ERROR] id={notification_id}: {e}")

    return NotificationStatus.DELIVERED if delivered else NotificationStatus.FAILED


# ---------------------------------------------------------------------------
# POST /notify — send a notification
# ---------------------------------------------------------------------------
@router.post("/notify", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def send_notification(request: NotificationRequest):
    """
    Send a notification via the specified channel.
    1. Dispatch to channel handler (mock / email / webhook)
    2. Store notification record in DB
    3. Update Prometheus metrics
    """
    notification_id = f"notif-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    # ── 1. Dispatch to channel ────────────────────────────────
    start = time.time()

    if request.channel == NotificationChannel.EMAIL:
        delivery_status = await _send_email(notification_id, request)
    elif request.channel == NotificationChannel.WEBHOOK:
        delivery_status = await _send_webhook(notification_id, request)
    else:
        delivery_status = _send_mock(notification_id, request)

    duration = time.time() - start
    notification_delivery_seconds.labels(channel=request.channel.value).observe(duration)

    # ── 2. Store in DB ────────────────────────────────────────
    try:
        with get_db_connection(autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notifications.notifications
                        (notification_id, incident_id, engineer, channel,
                         status, message, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        notification_id,
                        request.incident_id,
                        request.engineer,
                        request.channel.value,
                        delivery_status.value,
                        request.message,
                        now,
                    ),
                )
                cur.fetchone()
    except Exception as e:
        logger.error(f"Failed to store notification {notification_id}: {e}")
        # Notification was still sent — don't fail the request

    # ── 3. Update metrics ─────────────────────────────────────
    oncall_notifications_sent_total.labels(
        channel=request.channel.value,
        status=delivery_status.value,
    ).inc()

    return NotificationResponse(
        notification_id=notification_id,
        incident_id=request.incident_id,
        engineer=request.engineer,
        channel=request.channel,
        status=delivery_status,
        message=request.message,
        timestamp=now,
    )


# ---------------------------------------------------------------------------
# GET /notifications — list notification history
# ---------------------------------------------------------------------------
@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    incident_id: Optional[str] = None,
    channel: Optional[NotificationChannel] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """List notification history with optional filters."""
    conditions = []
    params: list = []

    if incident_id:
        conditions.append("incident_id = %s")
        params.append(incident_id)
    if channel:
        conditions.append("channel = %s")
        params.append(channel.value)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Total count
            cur.execute(
                f"SELECT COUNT(*) AS cnt FROM notifications.notifications {where}",
                params[:],
            )
            total = cur.fetchone()["cnt"]

            # Fetch page
            page_params = params + [limit, offset]
            cur.execute(
                f"""
                SELECT notification_id, incident_id, engineer, channel,
                       status, message, created_at
                FROM notifications.notifications
                {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                page_params,
            )
            rows = cur.fetchall()

    return NotificationListResponse(
        notifications=rows,
        total=total,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# GET /notifications/{notification_id} — single notification
# ---------------------------------------------------------------------------
@router.get("/notifications/{notification_id}")
async def get_notification(notification_id: str):
    """Get a single notification by its ID."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT notification_id, incident_id, engineer, channel,
                       status, message, created_at
                FROM notifications.notifications
                WHERE notification_id = %s
                """,
                (notification_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    return row
