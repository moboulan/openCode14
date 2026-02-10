"""Tests for database module utilities."""

from unittest.mock import MagicMock, patch

import pytest

from helpers import fake_connection, fake_connection_error


def test_check_database_health_true():
    """check_database_health returns True when query succeeds."""
    with patch("app.database.get_db_connection", side_effect=fake_connection([(1,)])):
        from app.database import check_database_health

        assert check_database_health() is True


def test_check_database_health_false():
    """check_database_health returns False when DB is unreachable."""
    with patch("app.database.get_db_connection", side_effect=fake_connection_error()):
        from app.database import check_database_health

        assert check_database_health() is False
