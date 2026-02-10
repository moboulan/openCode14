"""Tests for custom Prometheus metrics setup."""

from app.metrics import alerts_correlated_total, alerts_received_total, setup_custom_metrics


class TestMetrics:
    def test_setup_runs_without_error(self):
        """setup_custom_metrics should initialise without raising."""
        setup_custom_metrics()

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
