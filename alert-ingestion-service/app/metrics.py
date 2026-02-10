import logging

from prometheus_client import Counter

logger = logging.getLogger(__name__)

# Custom metrics for incident platform

# Counter: Total alerts received
alerts_received_total = Counter(
    "alerts_received_total", "Total number of alerts received", ["severity", "service"]
)

# Counter: Alerts correlated to incidents
alerts_correlated_total = Counter(
    "alerts_correlated_total",
    "Total number of alerts correlated to incidents",
    ["result"],
)


def setup_custom_metrics():
    """Initialize custom metrics"""
    logger.info("Custom Prometheus metrics initialized")


# Export metrics for use in other modules
__all__ = [
    "alerts_received_total",
    "alerts_correlated_total",
]
