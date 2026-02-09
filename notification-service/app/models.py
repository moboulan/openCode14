from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    MOCK = "mock"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"


class NotificationStatus(str, Enum):
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class NotificationRequest(BaseModel):
    """Request body for sending a notification."""

    incident_id: str = Field(..., description="Incident ID to notify about")
    engineer: str = Field(..., description="Engineer name or email to notify")
    channel: NotificationChannel = Field(
        default=NotificationChannel.MOCK,
        description="Notification channel (mock, email, webhook)",
    )
    message: str = Field(..., description="Notification message body")
    severity: Optional[SeverityLevel] = Field(None, description="Incident severity")
    webhook_url: Optional[str] = Field(None, description="Override webhook URL")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class NotificationResponse(BaseModel):
    """Response after sending a notification."""

    notification_id: str
    incident_id: str
    engineer: str
    channel: NotificationChannel
    status: NotificationStatus
    message: str
    timestamp: datetime


class NotificationHistoryItem(BaseModel):
    """Single notification in history list."""

    notification_id: str
    incident_id: str
    engineer: str
    channel: str
    status: str
    message: str
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""

    notifications: List[NotificationHistoryItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------


class HealthCheck(BaseModel):
    """Health check response model"""

    status: str
    timestamp: datetime
    service: str
    version: str
    uptime: float
    checks: Dict[str, str]
