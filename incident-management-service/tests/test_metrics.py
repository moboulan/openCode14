"""Tests for custom Prometheus metrics setup."""

from app.metrics import (
    incidents_total,
    open_incidents,
    incident_mtta_seconds,
    incident_mttr_seconds,
    setup_custom_metrics,
)


class TestMetrics:
    def test_setup_initializes_gauges(self):
        """setup_custom_metrics should set open_incidents gauge to 0 for all severities."""
        setup_custom_metrics()
        for severity in ["critical", "high", "medium", "low"]:
            val = open_incidents.labels(severity=severity)._value.get()
            assert val == 0.0

    def test_incidents_total_counter_increments(self):
        before = incidents_total.labels(status="open", severity="high")._value.get()
        incidents_total.labels(status="open", severity="high").inc()
        after = incidents_total.labels(status="open", severity="high")._value.get()
        assert after == before + 1

    def test_mtta_histogram_observes(self):
        """Observing MTTA should not raise."""
        incident_mtta_seconds.labels(severity="critical").observe(45.0)

    def test_mttr_histogram_observes(self):
        """Observing MTTR should not raise."""
        incident_mttr_seconds.labels(severity="low").observe(1800.0)

    def test_open_incidents_gauge_inc_dec(self):
        setup_custom_metrics()
        open_incidents.labels(severity="high").inc()
        val = open_incidents.labels(severity="high")._value.get()
        assert val == 1.0
        open_incidents.labels(severity="high").dec()
        val2 = open_incidents.labels(severity="high")._value.get()
        assert val2 == 0.0
