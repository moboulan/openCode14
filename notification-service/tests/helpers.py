"""Shared test helpers for notification-service tests.

Importable by test_api.py, test_notify.py, etc.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock


def fake_connection(cursor_sides: list[dict | None]):
    """Return a patched get_db_connection that yields a mock with preset cursor results.

    ``cursor_sides`` is a list of values that successive ``fetchone()`` / ``fetchall()``
    calls will return (one entry per ``with conn.cursor()`` block).
    """
    call_idx = {"i": 0}

    @contextmanager
    def _ctx(autocommit=False):
        conn = MagicMock()

        @contextmanager
        def _cur_ctx():
            cur = MagicMock()
            idx = call_idx["i"]
            if idx < len(cursor_sides):
                val = cursor_sides[idx]
                cur.fetchone.return_value = val
                cur.fetchall.return_value = val if isinstance(val, list) else [val] if val else []
            else:
                cur.fetchone.return_value = None
                cur.fetchall.return_value = []
            call_idx["i"] += 1
            yield cur

        conn.cursor = _cur_ctx
        yield conn

    return _ctx


class FakeAsyncClient:
    """Simulate a healthy external service."""

    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, *a, **kw):
        return FakeResponse(status_code=202)


class FakeAsyncClientDown:
    """Simulate external service being unreachable."""

    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, *a, **kw):
        raise Exception("connection refused")


class FakeResponse:
    """Simulate an HTTP response."""

    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body or {}
        self.text = str(body)

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")
