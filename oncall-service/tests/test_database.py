"""Tests for app/database.py -- pool lifecycle, get_db_connection, health check."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.db
def test_get_pool_creates_pool():
    """get_pool creates a new pool when none exists."""
    import app.database as db_mod

    original_pool = db_mod._connection_pool
    try:
        db_mod._connection_pool = None
        with patch.object(db_mod.pool, "ThreadedConnectionPool") as mock_cls:
            mock_cls.return_value = MagicMock(closed=False)
            p = db_mod.get_pool()
            mock_cls.assert_called_once()
            assert p is not None
    finally:
        db_mod._connection_pool = original_pool


def test_close_pool():
    """close_pool closes pool and sets to None."""
    mock_pool = MagicMock(closed=False)
    with patch("app.database._connection_pool", mock_pool):
        from app.database import close_pool

        close_pool()
        mock_pool.closeall.assert_called_once()


def test_close_pool_noop_when_none():
    """close_pool is a no-op when pool is None."""
    with patch("app.database._connection_pool", None):
        from app.database import close_pool

        close_pool()  # should not raise


def test_check_database_health_success():
    """check_database_health returns True when DB is reachable."""
    from helpers import fake_connection

    with patch("app.database.get_db_connection", fake_connection([{"?column?": 1}])):
        from app.database import check_database_health

        assert check_database_health() is True


def test_check_database_health_failure():
    """check_database_health returns False on DB error."""
    with patch("app.database.get_db_connection", side_effect=Exception("DB down")):
        from app.database import check_database_health

        assert check_database_health() is False


# ── get_db_connection context-manager paths ───────────────────


def test_get_db_connection_normal_path():
    """get_db_connection yields a connection and returns it to the pool."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.database.get_pool", return_value=mock_pool):
        from app.database import get_db_connection

        with get_db_connection() as conn:
            assert conn is mock_conn

        # Connection returned to pool
        mock_pool.putconn.assert_called_once_with(mock_conn)
        # No commit (autocommit=False)
        mock_conn.commit.assert_not_called()
        # No rollback (no error)
        mock_conn.rollback.assert_not_called()


def test_get_db_connection_autocommit():
    """get_db_connection commits on successful exit when autocommit=True."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.database.get_pool", return_value=mock_pool):
        from app.database import get_db_connection

        with get_db_connection(autocommit=True) as conn:
            assert conn is mock_conn

        mock_conn.commit.assert_called_once()
        mock_pool.putconn.assert_called_once_with(mock_conn)


def test_get_db_connection_rollback_on_error():
    """get_db_connection rolls back and re-raises on error inside the block."""
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_pool.getconn.return_value = mock_conn

    with patch("app.database.get_pool", return_value=mock_pool):
        from app.database import get_db_connection

        with pytest.raises(ValueError, match="boom"):
            with get_db_connection():
                raise ValueError("boom")

        mock_conn.rollback.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_pool.putconn.assert_called_once_with(mock_conn)
