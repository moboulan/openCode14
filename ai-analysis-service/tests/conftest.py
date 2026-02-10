"""
Shared fixtures for ai-analysis-service tests.

Uses httpx.ASGITransport so we never need a running server.
Database-hitting tests are marked with @pytest.mark.db and skipped
when no database is available.
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

# Provide a dummy DATABASE_URL for unit tests (DB is always mocked)
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

from helpers import fake_connection, fake_connection_error  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Ensure the app never tries to connect to a real DB during unit tests
# ---------------------------------------------------------------------------

_mock_pool = MagicMock()


@pytest.fixture(autouse=True)
def _patch_db_pool(request):
    """Patch the database pool for every test unless marked with @pytest.mark.db."""
    markers = {m.name for m in request.node.iter_markers()}
    if "db" in markers or "integration" in markers:
        yield
        return

    with patch("app.database._pool", _mock_pool):
        yield


# ---------------------------------------------------------------------------
# Mock the SimilarityEngine at module level to avoid scikit-learn startup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _patch_engine(request):
    """Inject a mock engine so tests don't depend on the NLP index."""
    markers = {m.name for m in request.node.iter_markers()}
    if "integration" in markers:
        yield
        return

    from app.nlp_engine import Suggestion

    mock_engine = MagicMock()
    mock_engine.analyse.return_value = [
        Suggestion(
            root_cause="Test root cause",
            solution="Test solution",
            confidence=0.85,
            source="knowledge_base",
            matched_pattern="test pattern match",
        )
    ]
    mock_engine._corpus_size = 20
    mock_engine._hist_entries = []

    with (
        patch("app.routers.api.engine", mock_engine),
        patch("app.main.engine", mock_engine),
    ):
        yield mock_engine


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
# Sample payloads
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_analyse_payload():
    return {
        "message": "High CPU usage detected on payment-api server",
        "service": "payment-api",
        "severity": "critical",
        "alert_id": "alert-123",
        "incident_id": "inc-456",
    }
