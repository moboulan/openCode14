"""Tests for app/metrics.py -- custom Prometheus metrics."""


def test_escalations_total_counter():
    """escalations_total counter increments per team."""
    from app.metrics import escalations_total

    before = escalations_total.labels(team="platform")._value.get()
    escalations_total.labels(team="platform").inc()
    after = escalations_total.labels(team="platform")._value.get()
    assert after == before + 1


def test_oncall_current_gauge():
    """oncall_current gauge can be set."""
    from app.metrics import oncall_current

    oncall_current.labels(team="backend", engineer="alice@example.com", role="primary").set(1)
    val = oncall_current.labels(team="backend", engineer="alice@example.com", role="primary")._value.get()
    assert val == 1.0


def test_setup_custom_metrics():
    """setup_custom_metrics runs without error."""
    from app.metrics import setup_custom_metrics

    setup_custom_metrics()  # should not raise
