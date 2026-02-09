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
