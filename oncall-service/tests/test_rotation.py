"""Unit tests for the rotation algorithm (_compute_current_oncall)."""

from datetime import date, datetime, timezone
from unittest.mock import patch

import pytest

from app.routers.api import _compute_current_oncall

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _schedule(
    rotation_type="weekly",
    start_date=date(2026, 1, 1),
    engineers=None,
):
    if engineers is None:
        engineers = [
            {"name": "Alice", "email": "alice@example.com", "primary": True},
            {"name": "Bob", "email": "bob@example.com", "primary": False},
            {"name": "Charlie", "email": "charlie@example.com", "primary": False},
        ]
    return {
        "rotation_type": rotation_type,
        "start_date": start_date,
        "engineers": engineers,
    }


# ---------------------------------------------------------------------------
# Weekly rotation
# ---------------------------------------------------------------------------


class TestWeeklyRotation:
    """Tests for weekly rotation logic."""

    @patch("app.routers.api.date")
    def test_week_0_returns_first_engineer(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, secondary = _compute_current_oncall(_schedule())
        assert primary.email == "alice@example.com"
        assert secondary.email == "bob@example.com"

    @patch("app.routers.api.date")
    def test_week_1_rotates_to_second(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 8)  # 7 days later
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, secondary = _compute_current_oncall(_schedule())
        assert primary.email == "bob@example.com"
        assert secondary.email == "charlie@example.com"

    @patch("app.routers.api.date")
    def test_week_wraps_around(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 22)  # 21 days = 3 weeks -> idx 0
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, secondary = _compute_current_oncall(_schedule())
        assert primary.email == "alice@example.com"
        assert secondary.email == "bob@example.com"


# ---------------------------------------------------------------------------
# Daily rotation
# ---------------------------------------------------------------------------


class TestDailyRotation:
    """Tests for daily rotation logic."""

    @patch("app.routers.api.date")
    def test_day_0_returns_first(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, secondary = _compute_current_oncall(_schedule(rotation_type="daily"))
        assert primary.email == "alice@example.com"

    @patch("app.routers.api.date")
    def test_day_1_rotates(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 2)  # 1 day later
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, secondary = _compute_current_oncall(_schedule(rotation_type="daily"))
        assert primary.email == "bob@example.com"
        assert secondary.email == "charlie@example.com"

    @patch("app.routers.api.date")
    def test_daily_wraps_around(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 4)  # 3 days -> idx 0
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, secondary = _compute_current_oncall(_schedule(rotation_type="daily"))
        assert primary.email == "alice@example.com"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case tests for rotation logic."""

    def test_empty_engineers_returns_none(self):
        primary, secondary = _compute_current_oncall(_schedule(engineers=[]))
        assert primary is None
        assert secondary is None

    @patch("app.routers.api.date")
    def test_single_engineer_no_secondary(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        engineers = [{"name": "Alice", "email": "alice@example.com", "primary": True}]
        primary, secondary = _compute_current_oncall(_schedule(engineers=engineers))
        assert primary.email == "alice@example.com"
        assert secondary is None

    @patch("app.routers.api.date")
    def test_start_date_in_future_uses_idx_zero(self, mock_date):
        mock_date.today.return_value = date(2025, 6, 1)  # before start
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, _ = _compute_current_oncall(_schedule(start_date=date(2026, 1, 1)))
        assert primary.email == "alice@example.com"

    @patch("app.routers.api.date")
    def test_start_date_as_string(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, _ = _compute_current_oncall(_schedule(start_date="2026-01-01"))
        assert primary.email == "alice@example.com"

    @patch("app.routers.api.date")
    def test_start_date_as_datetime(self, mock_date):
        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        primary, _ = _compute_current_oncall(_schedule(start_date=datetime(2026, 1, 1, tzinfo=timezone.utc)))
        assert primary.email == "alice@example.com"

    @patch("app.routers.api.date")
    def test_engineers_as_json_string(self, mock_date):
        import json

        mock_date.today.return_value = date(2026, 1, 1)
        mock_date.fromisoformat = date.fromisoformat
        mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
        engineers = json.dumps(
            [
                {"name": "Alice", "email": "alice@example.com", "primary": True},
                {"name": "Bob", "email": "bob@example.com", "primary": False},
            ]
        )
        primary, secondary = _compute_current_oncall(_schedule(engineers=engineers))
        assert primary.email == "alice@example.com"
        assert secondary.email == "bob@example.com"
