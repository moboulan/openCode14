import logging

from prometheus_client import Counter, Gauge, Histogram

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

# Total incidents by status and severity
incidents_total = Counter("incidents_total", "Total number of incidents", ["status", "severity"])

# Notifications sent (used when this service triggers a notification)
notifications_sent_total = Counter("oncall_notifications_sent_total", "Total notifications sent", ["channel", "status"])

# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------

# Mean Time To Acknowledge
incident_mtta_seconds = Histogram(
    "incident_mtta_seconds",
    "Time to acknowledge incidents in seconds",
    ["severity"],
    buckets=settings.mtta_bucket_list,
)

# Mean Time To Resolve
incident_mttr_seconds = Histogram(
    "incident_mttr_seconds",
    "Time to resolve incidents in seconds",
    ["severity"],
    buckets=settings.mttr_bucket_list,
)

# ---------------------------------------------------------------------------
# Gauges
# ---------------------------------------------------------------------------

open_incidents = Gauge("open_incidents", "Current number of open incidents", ["severity"])


def setup_custom_metrics():
    """Initialize custom metrics — set gauges to 0."""
    logger.info("Custom Prometheus metrics initialized")
    for severity in ["critical", "high", "medium", "low"]:
        open_incidents.labels(severity=severity).set(0)


__all__ = [
    "incidents_total",
    "notifications_sent_total",
    "incident_mtta_seconds",
    "incident_mttr_seconds",
    "open_incidents",
]
