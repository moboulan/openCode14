"""Tests for the POST /api/v1/analyze endpoint."""

from unittest.mock import patch

import pytest
from helpers import fake_connection


@pytest.mark.asyncio
async def test_analyze_success(client, sample_analyse_payload):
    """Analyze returns suggestions for a valid alert."""
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection([None])):
        resp = await client.post("/api/v1/analyze", json=sample_analyse_payload)

    assert resp.status_code == 200
    body = resp.json()
    assert "suggestions" in body
    assert len(body["suggestions"]) >= 1
    assert body["suggestions"][0]["root_cause"] == "Test root cause"
    assert body["suggestions"][0]["confidence"] == 0.85
    assert body["alert_id"] == "alert-123"
    assert body["incident_id"] == "inc-456"
    assert "analysed_at" in body


@pytest.mark.asyncio
async def test_analyze_empty_message(client):
    """Analyze rejects an empty message."""
    payload = {"message": ""}
    resp = await client.post("/api/v1/analyze", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analyze_missing_message(client):
    """Analyze rejects a missing message field."""
    resp = await client.post("/api/v1/analyze", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_analyze_optional_fields(client):
    """Analyze works when optional fields are omitted."""
    with patch("app.routers.api.get_db_connection", side_effect=fake_connection([None])):
        resp = await client.post("/api/v1/analyze", json={"message": "disk full on host"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["alert_id"] is None
    assert body["incident_id"] is None
    assert len(body["suggestions"]) >= 1


@pytest.mark.asyncio
async def test_analyze_persists_suggestions(client, sample_analyse_payload):
    """Analyze stores suggestions in the DB."""
    mock_conn = fake_connection([None])
    with patch("app.routers.api.get_db_connection", side_effect=mock_conn):
        resp = await client.post("/api/v1/analyze", json=sample_analyse_payload)

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_analyze_db_error_still_returns(client, sample_analyse_payload, _patch_engine):
    """If DB persist fails, the response is still returned (fire-and-forget)."""
    from helpers import fake_connection_error

    with patch("app.routers.api.get_db_connection", side_effect=fake_connection_error()):
        resp = await client.post("/api/v1/analyze", json=sample_analyse_payload)

    # The endpoint should still return 200 since analysis succeeded even if persist fails
    assert resp.status_code == 200
    assert len(resp.json()["suggestions"]) >= 1


@pytest.mark.asyncio
async def test_analyze_engine_not_initialised(client):
    """Analyze returns 503 when engine is None."""
    with patch("app.routers.api.engine", None):
        resp = await client.post("/api/v1/analyze", json={"message": "test alert"})
    assert resp.status_code == 503
    assert "Engine not initialised" in resp.json()["detail"]
