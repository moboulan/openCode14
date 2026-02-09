"""Tests for database module."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.database import check_database_health, close_pool, get_pool, get_db_connection


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


def test_get_pool_creates_pool():
    """get_pool creates a new pool when none exists."""
    with patch("app.database._connection_pool", None):
        with patch("app.database.pool.ThreadedConnectionPool") as mock_tcp:
            mock_pool_instance = MagicMock()
            mock_tcp.return_value = mock_pool_instance
            result = get_pool()
            mock_tcp.assert_called_once()
            assert result == mock_pool_instance


def test_get_pool_recreates_when_closed():
    """get_pool creates a new pool when existing one is closed."""
    mock_old_pool = MagicMock()
    mock_old_pool.closed = True

    with patch("app.database._connection_pool", mock_old_pool):
        with patch("app.database.pool.ThreadedConnectionPool") as mock_tcp:
            mock_new_pool = MagicMock()
            mock_tcp.return_value = mock_new_pool
            result = get_pool()
            mock_tcp.assert_called_once()
            assert result == mock_new_pool


def test_get_db_connection_yields_conn_and_puts_back():
    """get_db_connection yields a connection and returns it to the pool."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.database.get_pool", return_value=mock_pool):
        with get_db_connection() as conn:
            assert conn == mock_conn

    mock_pool.putconn.assert_called_once_with(mock_conn)


def test_get_db_connection_autocommit():
    """get_db_connection commits when autocommit=True."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.database.get_pool", return_value=mock_pool):
        with get_db_connection(autocommit=True) as conn:
            pass  # normal flow

    mock_conn.commit.assert_called_once()
    mock_pool.putconn.assert_called_once_with(mock_conn)


def test_get_db_connection_no_autocommit():
    """get_db_connection does not commit when autocommit=False."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.database.get_pool", return_value=mock_pool):
        with get_db_connection(autocommit=False) as conn:
            pass

    mock_conn.commit.assert_not_called()
    mock_pool.putconn.assert_called_once_with(mock_conn)


def test_get_db_connection_rollback_on_exception():
    """get_db_connection rolls back and re-raises on exception."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.database.get_pool", return_value=mock_pool):
        with pytest.raises(ValueError):
            with get_db_connection() as conn:
                raise ValueError("test error")

    mock_conn.rollback.assert_called_once()
    mock_pool.putconn.assert_called_once_with(mock_conn)
