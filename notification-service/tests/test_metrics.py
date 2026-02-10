"""Tests for notification service metrics."""

from app.metrics import (
    notification_delivery_seconds,
    oncall_notifications_sent_total,
    setup_custom_metrics,
)


def test_setup_custom_metrics():
    """setup_custom_metrics should not raise."""
    setup_custom_metrics()


def test_oncall_notifications_sent_total():
    """Counter oncall_notifications_sent_total increments correctly."""
    before = oncall_notifications_sent_total.labels(
        channel="mock", status="delivered"
    )._value.get()
    oncall_notifications_sent_total.labels(channel="mock", status="delivered").inc()
    after = oncall_notifications_sent_total.labels(
        channel="mock", status="delivered"
    )._value.get()
    assert after == before + 1


def test_notification_delivery_histogram():
    """Histogram notification_delivery_seconds can observe values."""
    notification_delivery_seconds.labels(channel="mock").observe(0.5)
    # Just ensure it doesn't raise
