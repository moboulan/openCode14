"""
Shared fixtures for incident-management-service tests.

Uses httpx.ASGITransport so we never need a running server.
Database-hitting tests are marked with @pytest.mark.db and skipped
when no database is available (CI stage 5 supplies one).
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport

# Provide a dummy DATABASE_URL for unit tests (DB is always mocked)
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

# Re-export helpers so tests can import from conftest or helpers
from helpers import fake_connection  # noqa: F401

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

    with patch("app.database._connection_pool", _mock_pool), \
         patch("app.database.get_pool", return_value=_mock_pool):
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_incident_payload():
    return {
        "title": "[LOW] test-svc: Unit test incident",
        "service": "test-svc",
        "severity": "low",
        "description": "Created by unit test",
    }
