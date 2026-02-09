import logging

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

# Total notifications sent by channel and delivery status
oncall_notifications_sent_total = Counter(
    "oncall_notifications_sent_total",
    "Total notifications sent",
    ["channel", "status"],
)

# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------

# Notification delivery latency
notification_delivery_seconds = Histogram(
    "notification_delivery_seconds",
    "Time to deliver notifications in seconds",
    ["channel"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)


def setup_custom_metrics():
    """Initialize custom metrics."""
    logger.info("Custom Prometheus metrics initialized")


__all__ = [
    "oncall_notifications_sent_total",
    "notification_delivery_seconds",
]
