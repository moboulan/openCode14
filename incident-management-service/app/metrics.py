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
    """Initialize custom metrics — sync gauge from actual DB state."""
    logger.info("Custom Prometheus metrics initialized")
    # Default all severities to 0
    for severity in ["critical", "high", "medium", "low"]:
        open_incidents.labels(severity=severity).set(0)

    # Sync from DB: count actual open incidents per severity
    try:
        from app.database import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT severity::text, COUNT(*) AS cnt
                    FROM incidents.incidents
                    WHERE status IN ('open', 'acknowledged', 'in_progress', 'investigating')
                    GROUP BY severity
                    """)
                rows = cur.fetchall()
                for row in rows:
                    open_incidents.labels(severity=row["severity"]).set(row["cnt"])
                    logger.info(f"Gauge open_incidents[{row['severity']}] = {row['cnt']}")
    except Exception as e:
        logger.warning(f"Could not sync open_incidents gauge from DB: {e}")


__all__ = [
    "incidents_total",
    "notifications_sent_total",
    "incident_mtta_seconds",
    "incident_mttr_seconds",
    "open_incidents",
]
