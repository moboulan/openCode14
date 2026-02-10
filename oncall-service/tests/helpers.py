"""Shared test helpers for oncall-service tests.

Importable by test_api.py, etc.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock


def fake_connection(cursor_sides: list[dict | None]):
    """Return a patched get_db_connection that yields a mock with preset cursor results.

    ``cursor_sides`` is a list of values that successive ``fetchone()`` / ``fetchall()``
    calls will return (one entry per ``with conn.cursor()`` block).

    If an entry is an ``Exception`` instance the corresponding ``get_db_connection``
    invocation will raise that exception instead of yielding a connection.
    """
    call_idx = {"i": 0}

    @contextmanager
    def _ctx(autocommit=False):
        idx = call_idx["i"]
        # Support raising exceptions at a specific call index
        if idx < len(cursor_sides) and isinstance(cursor_sides[idx], Exception):
            call_idx["i"] += 1
            raise cursor_sides[idx]

        conn = MagicMock()

        @contextmanager
        def _cur_ctx():
            cur = MagicMock()
            i = call_idx["i"]
            if i < len(cursor_sides):
                val = cursor_sides[i]
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

    async def __aexit__(self, *args):
        pass

    async def get(self, url, **kw):
        return FakeResponse(200, {"status": "healthy"})

    async def post(self, url, **kw):
        return FakeResponse(200, {"status": "ok"})


class FakeAsyncClientDown:
    """Simulate an unreachable external service."""

    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def get(self, url, **kw):
        raise ConnectionError("Service unavailable")

    async def post(self, url, **kw):
        raise ConnectionError("Service unavailable")


class FakeResponse:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json


def make_fake_async_client(get_status=200, get_json=None, post_status=200, post_json=None):
    """Factory that returns a FakeAsyncClient class with configurable responses."""

    class _Client:
        def __init__(self, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, url, **kw):
            return FakeResponse(get_status, get_json or {"status": "ok"})

        async def post(self, url, **kw):
            return FakeResponse(post_status, post_json or {"status": "ok"})

    return _Client
