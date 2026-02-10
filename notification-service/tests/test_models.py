"""Tests for notification service models (Pydantic validation)."""

import pytest
from app.models import (NotificationChannel, NotificationRequest,
                        NotificationStatus, SeverityLevel)
from pydantic import ValidationError


def test_notification_request_valid():
    """Valid NotificationRequest should be created successfully."""
    req = NotificationRequest(
        incident_id="inc-123",
        engineer="alice@example.com",
        channel="mock",
        message="Test notification",
    )
    assert req.incident_id == "inc-123"
    assert req.channel == NotificationChannel.MOCK
    assert req.severity is None
    assert req.webhook_url is None


def test_notification_request_with_severity():
    """NotificationRequest with optional severity."""
    req = NotificationRequest(
        incident_id="inc-456",
        engineer="bob@example.com",
        channel="webhook",
        message="Critical alert",
        severity="critical",
    )
    assert req.severity == SeverityLevel.CRITICAL
    assert req.channel == NotificationChannel.WEBHOOK


def test_notification_request_missing_fields():
    """Missing required fields raises ValidationError."""
    with pytest.raises(ValidationError):
        NotificationRequest(incident_id="inc-789")


def test_notification_request_invalid_channel():
    """Invalid channel raises ValidationError."""
    with pytest.raises(ValidationError):
        NotificationRequest(
            incident_id="inc-789",
            engineer="test@test.com",
            channel="INVALID",
            message="test",
        )


def test_notification_channel_enum():
    """NotificationChannel enum values."""
    assert NotificationChannel.MOCK == "mock"
    assert NotificationChannel.EMAIL == "email"
    assert NotificationChannel.WEBHOOK == "webhook"
    assert NotificationChannel.SLACK == "slack"


def test_notification_status_enum():
    """NotificationStatus enum values."""
    assert NotificationStatus.SENT == "sent"
    assert NotificationStatus.DELIVERED == "delivered"
    assert NotificationStatus.FAILED == "failed"


def test_severity_level_enum():
    """SeverityLevel enum values."""
    assert SeverityLevel.CRITICAL == "critical"
    assert SeverityLevel.HIGH == "high"
    assert SeverityLevel.MEDIUM == "medium"
    assert SeverityLevel.LOW == "low"


def test_notification_request_default_channel():
    """Default channel should be mock."""
    req = NotificationRequest(
        incident_id="inc-default",
        engineer="test@test.com",
        message="test default channel",
    )
    assert req.channel == NotificationChannel.MOCK
