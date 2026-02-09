"""Tests for database module."""

from unittest.mock import MagicMock, patch

import pytest

from app.database import check_database_health, close_pool


def test_check_database_health_success():
    """check_database_health returns True when DB is reachable."""
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

    with patch("app.database.get_db_connection") as mock_get:
        mock_get.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get.return_value.__exit__ = MagicMock(return_value=False)
        result = check_database_health()

    assert result is True


def test_check_database_health_failure():
    """check_database_health returns False when DB is unreachable."""
    with patch("app.database.get_db_connection", side_effect=Exception("connection refused")):
        result = check_database_health()
    assert result is False


def test_close_pool_when_open():
    """close_pool closes the pool when it's open."""
    mock_pool = MagicMock()
    mock_pool.closed = False

    with patch("app.database._connection_pool", mock_pool):
        close_pool()

    mock_pool.closeall.assert_called_once()


def test_close_pool_when_none():
    """close_pool does nothing when pool is None."""
    with patch("app.database._connection_pool", None):
        close_pool()  # Should not raise
