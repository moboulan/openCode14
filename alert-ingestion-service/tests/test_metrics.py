"""Tests for custom Prometheus metrics setup."""

from app.metrics import (
    alerts_received_total,
    alerts_correlated_total,
    incidents_total,
    open_incidents,
    setup_custom_metrics,
)


class TestMetrics:
    def test_setup_initializes_gauges(self):
        """setup_custom_metrics should set open_incidents gauge to 0 for all severities."""
        setup_custom_metrics()
        for severity in ["critical", "high", "medium", "low"]:
            val = open_incidents.labels(severity=severity)._value.get()
            assert val == 0.0

    def test_alerts_received_counter_increments(self):
        before = alerts_received_total.labels(severity="low", service="test-svc")._value.get()
        alerts_received_total.labels(severity="low", service="test-svc").inc()
        after = alerts_received_total.labels(severity="low", service="test-svc")._value.get()
        assert after == before + 1

    def test_alerts_correlated_counter_increments(self):
        before = alerts_correlated_total.labels(result="new_incident")._value.get()
        alerts_correlated_total.labels(result="new_incident").inc()
        after = alerts_correlated_total.labels(result="new_incident")._value.get()
        assert after == before + 1

    def test_incidents_total_counter_increments(self):
        before = incidents_total.labels(status="open", severity="high")._value.get()
        incidents_total.labels(status="open", severity="high").inc()
        after = incidents_total.labels(status="open", severity="high")._value.get()
        assert after == before + 1
