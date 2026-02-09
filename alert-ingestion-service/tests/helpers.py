"""Shared test helpers for alert-ingestion-service tests.

Importable by test_api.py, test_correlation.py, etc.
"""

import uuid
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


class FakeIncidentResponse:
    """Simulate a successful incident-management POST response."""
    status_code = 201

    def __init__(self, incident_id="inc-new-111", db_id=None):
        self._incident_id = incident_id
        self._db_id = db_id or str(uuid.uuid4())

    def raise_for_status(self):
        pass

    def json(self):
        return {"incident_id": self._incident_id, "id": self._db_id}


class FakeAsyncClient:
    """Simulate a healthy incident-management service."""
    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, *a, **kw):
        return FakeIncidentResponse()


class FakeAsyncClientDown:
    """Simulate incident service being unreachable."""
    def __init__(self, **kw):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def post(self, *a, **kw):
        raise Exception("connection refused")
