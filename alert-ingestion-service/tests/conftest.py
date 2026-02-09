"""
Shared fixtures for alert-ingestion-service tests.

Uses httpx.ASGITransport so we never need a running server.
Database-hitting tests are marked with @pytest.mark.db and skipped
when no database is available (CI stage 5 supplies one).
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

# ---------------------------------------------------------------------------
# Ensure the app never tries to connect to a real DB during unit tests
# ---------------------------------------------------------------------------

_mock_pool = MagicMock()


@pytest.fixture(autouse=True)
def _patch_db_pool(request):
    """Patch the database pool for every test unless marked with @pytest.mark.db."""
    if "db" in {m.name for m in request.node.iter_markers()}:
        yield  # real DB
        return

    with patch("app.database._connection_pool", _mock_pool), \
         patch("app.database.get_pool", return_value=_mock_pool):
        yield


@pytest.fixture()
def mock_db_connection():
    """Provide a mock get_db_connection context manager."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# Async client fixture (talks directly to the ASGI app)
# ---------------------------------------------------------------------------

@pytest.fixture()
async def client():
    """Async test client bound to the FastAPI app."""
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_alert_payload():
    return {
        "service": "test-service",
        "severity": "low",
        "message": "Unit-test alert",
        "labels": {"env": "test"},
    }
