import logging

from prometheus_client import Counter, Gauge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

# Escalations triggered per team
escalations_total = Counter(
    "escalations_total",
    "Total escalations triggered",
    ["team"],
)

# ---------------------------------------------------------------------------
# Gauges
# ---------------------------------------------------------------------------

# Current on-call engineer per team (1 = on-call, 0 = off)
oncall_current = Gauge(
    "oncall_current",
    "Current on-call status per team",
    ["team", "engineer", "role"],
)


def setup_custom_metrics():
    """Initialize custom metrics."""
    logger.info("Custom Prometheus metrics initialized")


__all__ = [
    "escalations_total",
    "oncall_current",
]
