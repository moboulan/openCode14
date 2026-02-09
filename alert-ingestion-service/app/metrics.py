import logging

from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# Custom metrics for incident platform

# Counter: Total alerts received
alerts_received_total = Counter("alerts_received_total", "Total number of alerts received", ["severity", "service"])

# Counter: Alerts correlated to incidents
alerts_correlated_total = Counter(
    "alerts_correlated_total", "Total number of alerts correlated to incidents", ["result"]
)

# Counter: Total incidents created
incidents_total = Counter("incidents_total", "Total number of incidents", ["status", "severity"])

# Histogram: Mean Time To Acknowledge (MTTA)
incident_mtta_seconds = Histogram(
    "incident_mtta_seconds",
    "Time to acknowledge incidents in seconds",
    ["severity"],
    buckets=[30, 60, 120, 300, 600, 1800, 3600],  # 30s to 1 hour
)

# Histogram: Mean Time To Resolve (MTTR)
incident_mttr_seconds = Histogram(
    "incident_mttr_seconds",
    "Time to resolve incidents in seconds",
    ["severity"],
    buckets=[300, 600, 1800, 3600, 7200, 14400, 28800],  # 5 min to 8 hours
)

# Gauge: Open incidents count
open_incidents = Gauge("open_incidents", "Current number of open incidents", ["severity"])

# Counter: Notifications sent
notifications_sent_total = Counter("oncall_notifications_sent_total", "Total notifications sent", ["channel", "status"])

# Counter: Escalations
escalations_total = Counter("escalations_total", "Total number of escalations", ["team", "reason"])


def setup_custom_metrics():
    """Initialize custom metrics"""
    logger.info("Custom Prometheus metrics initialized")

    # Initialize gauges to 0
    for severity in ["critical", "high", "medium", "low"]:
        open_incidents.labels(severity=severity).set(0)


# Export metrics for use in other modules
__all__ = [
    "alerts_received_total",
    "alerts_correlated_total",
    "incidents_total",
    "incident_mtta_seconds",
    "incident_mttr_seconds",
    "open_incidents",
    "notifications_sent_total",
    "escalations_total",
]
