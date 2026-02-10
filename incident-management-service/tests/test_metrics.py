"""Tests for custom Prometheus metrics setup."""

from app.metrics import (
    incident_mtta_seconds,
    incident_mttr_seconds,
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

    def test_setup_syncs_from_db(self):
        """setup_custom_metrics syncs open_incidents from DB when available."""
        from contextlib import contextmanager
        from unittest.mock import MagicMock, patch

        @contextmanager
        def _fake_conn(autocommit=False):
            conn = MagicMock()

            @contextmanager
            def _cur():
                cur = MagicMock()
                cur.fetchall.return_value = [
                    {"severity": "critical", "cnt": 3},
                    {"severity": "high", "cnt": 7},
                ]
                yield cur

            conn.cursor = _cur
            yield conn

        with patch("app.database.get_db_connection", _fake_conn):
            setup_custom_metrics()

        assert open_incidents.labels(severity="critical")._value.get() == 3.0
        assert open_incidents.labels(severity="high")._value.get() == 7.0

    def test_setup_handles_db_failure(self):
        """setup_custom_metrics handles DB failure gracefully (except branch)."""
        from contextlib import contextmanager
        from unittest.mock import patch

        @contextmanager
        def _fail_conn(autocommit=False):
            raise ConnectionError("DB unavailable")

        with patch("app.database.get_db_connection", _fail_conn):
            setup_custom_metrics()  # should not raise

        # Gauges should still be at 0 defaults
        for severity in ["critical", "high", "medium", "low"]:
            assert open_incidents.labels(severity=severity)._value.get() == 0.0
