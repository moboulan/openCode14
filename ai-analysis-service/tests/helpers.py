"""Shared test helpers for ai-analysis-service tests."""

from contextlib import contextmanager
from unittest.mock import MagicMock


def fake_connection(cursor_sides: list):
    """Return a patched get_db_connection that yields a mock with preset cursor results.

    ``cursor_sides`` is a list of values that successive ``with conn.cursor()`` blocks will return.
    """
    call_idx = {"i": 0}

    @contextmanager
    def _ctx():
        conn = MagicMock()

        @contextmanager
        def _cur_ctx():
            cur = MagicMock()
            idx = call_idx["i"]
            if idx < len(cursor_sides):
                val = cursor_sides[idx]
                cur.fetchone.return_value = val
                cur.fetchall.return_value = (
                    val if isinstance(val, list) else [val] if val else []
                )
            else:
                cur.fetchone.return_value = None
                cur.fetchall.return_value = []
            call_idx["i"] += 1
            yield cur

        conn.cursor = _cur_ctx
        yield conn

    return _ctx


def fake_connection_error():
    """Return a patched get_db_connection that raises an exception."""

    @contextmanager
    def _ctx():
        raise Exception("DB connection failed")

    return _ctx
