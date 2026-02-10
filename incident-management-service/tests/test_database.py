"""Tests for app/database.py — pool lifecycle, get_db_connection, health check."""

from unittest.mock import MagicMock, patch

import pytest

import app.database as db_mod

# All tests in this file manage the pool mock themselves
pytestmark = pytest.mark.db


class TestGetPool:
    def setup_method(self):
        """Reset pool state before each test."""
        self._original = db_mod._connection_pool

    def teardown_method(self):
        db_mod._connection_pool = self._original

    def test_creates_pool_when_none(self):
        db_mod._connection_pool = None
        with patch.object(db_mod.pool, "ThreadedConnectionPool") as MockPool:
            mock_instance = MagicMock()
            mock_instance.closed = False
            MockPool.return_value = mock_instance

            result = db_mod.get_pool()
            MockPool.assert_called_once()
            assert result is mock_instance

    def test_returns_existing_pool(self):
        mock_pool = MagicMock()
        mock_pool.closed = False
        db_mod._connection_pool = mock_pool

        with patch.object(db_mod.pool, "ThreadedConnectionPool") as MockPool:
            result = db_mod.get_pool()
            MockPool.assert_not_called()
            assert result is mock_pool

    def test_recreates_pool_when_closed(self):
        old_pool = MagicMock()
        old_pool.closed = True
        db_mod._connection_pool = old_pool

        with patch.object(db_mod.pool, "ThreadedConnectionPool") as MockPool:
            new_pool = MagicMock()
            new_pool.closed = False
            MockPool.return_value = new_pool

            result = db_mod.get_pool()
            MockPool.assert_called_once()
            assert result is new_pool


class TestGetDbConnection:
    def test_yields_connection_and_returns(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch("app.database.get_pool", return_value=mock_pool):
            from app.database import get_db_connection

            with get_db_connection() as conn:
                assert conn == mock_conn

            mock_pool.putconn.assert_called_once_with(mock_conn)
            mock_conn.commit.assert_not_called()

    def test_autocommit_true(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch("app.database.get_pool", return_value=mock_pool):
            from app.database import get_db_connection

            with get_db_connection(autocommit=True):
                pass

            mock_conn.commit.assert_called_once()
            mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_rollback_on_exception(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn

        with patch("app.database.get_pool", return_value=mock_pool):
            from app.database import get_db_connection

            with pytest.raises(ValueError):
                with get_db_connection():
                    raise ValueError("boom")

            mock_conn.rollback.assert_called_once()
            mock_pool.putconn.assert_called_once_with(mock_conn)


class TestClosePool:
    def test_closes_open_pool(self):
        mock_pool = MagicMock()
        mock_pool.closed = False

        with patch.object(db_mod, "_connection_pool", mock_pool):
            db_mod.close_pool()
            mock_pool.closeall.assert_called_once()

    def test_noop_when_no_pool(self):
        with patch.object(db_mod, "_connection_pool", None):
            db_mod.close_pool()  # should not raise


class TestCheckDatabaseHealth:
    def test_healthy(self):
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        with patch("app.database.get_pool", return_value=mock_pool):
            from app.database import check_database_health

            assert check_database_health() is True
            mock_cursor.execute.assert_called_once_with("SELECT 1")

    def test_unhealthy(self):
        with patch("app.database.get_pool", side_effect=Exception("no db")):
            from app.database import check_database_health

            assert check_database_health() is False
