"""
Shared fixtures for alert-ingestion-service tests.

Uses httpx.ASGITransport so we never need a running server.
Database-hitting tests are marked with @pytest.mark.db and skipped
when no database is available (CI stage 5 supplies one).
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Provide a dummy DATABASE_URL for unit tests (DB is always mocked)
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

# Re-export helpers so they stay accessible from conftest if needed
from helpers import (  # noqa: F401
    FakeAsyncClient,
    FakeAsyncClientDown,
    fake_connection,
)

# ---------------------------------------------------------------------------
# Ensure the app never tries to connect to a real DB during unit tests
# ---------------------------------------------------------------------------

_mock_pool = MagicMock()


@pytest.fixture(autouse=True)
def _patch_db_pool(request):
    """Patch the database pool for every test unless marked with @pytest.mark.db or @pytest.mark.integration."""
    markers = {m.name for m in request.node.iter_markers()}
    if "db" in markers or "integration" in markers:
        yield  # real DB
        return

    with patch("app.database._connection_pool", _mock_pool), patch("app.database.get_pool", return_value=_mock_pool):
        yield


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


@pytest.fixture()
def sample_alert_payload():
    return {
        "service": "test-service",
        "severity": "low",
        "message": "Unit-test alert",
        "labels": {"env": "test"},
    }
