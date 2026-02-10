import logging

from prometheus_client import Counter, Gauge, Histogram

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

# Notifications sent during escalation
escalation_notifications_total = Counter(
    "escalation_notifications_total",
    "Total notifications sent during escalation",
    ["team", "channel", "status"],
)

# Auto-escalation runs
auto_escalation_runs_total = Counter(
    "auto_escalation_runs_total",
    "Total automatic escalation check runs",
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

# Active escalation timers
active_escalation_timers = Gauge(
    "active_escalation_timers",
    "Number of active escalation timers",
    ["team"],
)

# Escalation rate (% of incidents that needed escalation)
escalation_rate = Gauge(
    "escalation_rate_percent",
    "Percentage of incidents that required escalation",
)

# ---------------------------------------------------------------------------
# Histograms
# ---------------------------------------------------------------------------

# Escalation response time (time from escalation to acknowledgment)
escalation_response_seconds = Histogram(
    "escalation_response_seconds",
    "Time from escalation to acknowledgment in seconds",
    ["team"],
    buckets=[30, 60, 120, 300, 600, 900, 1800],
)


def setup_custom_metrics():
    """Initialize custom metrics."""
    logger.info("Custom Prometheus metrics initialized")


__all__ = [
    "escalations_total",
    "escalation_notifications_total",
    "auto_escalation_runs_total",
    "oncall_current",
    "active_escalation_timers",
    "escalation_rate",
    "escalation_response_seconds",
]
