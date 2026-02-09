"""Tests for Pydantic models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models import (
    Alert,
    AlertResponse,
    HealthCheck,
    SeverityLevel,
    IncidentStatus,
)


# ── SeverityLevel enum ───────────────────────────────────────

class TestSeverityLevel:
    def test_values(self):
        assert set(SeverityLevel) == {
            SeverityLevel.CRITICAL,
            SeverityLevel.HIGH,
            SeverityLevel.MEDIUM,
            SeverityLevel.LOW,
        }

    def test_string_values(self):
        assert SeverityLevel.CRITICAL.value == "critical"
        assert SeverityLevel.HIGH.value == "high"
        assert SeverityLevel.MEDIUM.value == "medium"
        assert SeverityLevel.LOW.value == "low"


# ── IncidentStatus enum ─────────────────────────────────────

class TestIncidentStatus:
    def test_values(self):
        expected = {"open", "acknowledged", "in_progress", "resolved"}
        assert {s.value for s in IncidentStatus} == expected


# ── Alert model ──────────────────────────────────────────────

class TestAlertModel:
    def test_valid_alert_minimal(self):
        alert = Alert(service="web", severity="critical", message="down")
        assert alert.service == "web"
        assert alert.severity == SeverityLevel.CRITICAL
        assert alert.message == "down"
        assert alert.labels == {}
        assert alert.timestamp is not None  # auto-generated

    def test_valid_alert_full(self):
        ts = datetime(2026, 1, 1, tzinfo=timezone.utc)
        alert = Alert(
            service="api-gateway",
            severity="low",
            message="high latency",
            labels={"env": "prod", "region": "eu"},
            timestamp=ts,
        )
        assert alert.labels == {"env": "prod", "region": "eu"}
        assert alert.timestamp == ts

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError):
            Alert(service="x", severity="INVALID", message="boom")

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            Alert(service="x")  # missing severity, message


# ── AlertResponse model ──────────────────────────────────────

class TestAlertResponseModel:
    def test_valid_response(self):
        resp = AlertResponse(
            alert_id="alert-abc123",
            incident_id="inc-001",
            status="processed",
            action="new_incident",
            timestamp=datetime.now(timezone.utc),
        )
        assert resp.alert_id == "alert-abc123"
        assert resp.incident_id == "inc-001"

    def test_incident_id_optional(self):
        resp = AlertResponse(
            alert_id="alert-abc123",
            status="processed",
            action="new_incident",
            timestamp=datetime.now(timezone.utc),
        )
        assert resp.incident_id is None


# ── HealthCheck model ────────────────────────────────────────

class TestHealthCheckModel:
    def test_valid_health_check(self):
        hc = HealthCheck(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            service="alert-ingestion",
            version="1.0.0",
            uptime=123.45,
            checks={"database": "healthy", "memory": "healthy"},
        )
        assert hc.status == "healthy"
        assert hc.uptime == 123.45
        assert hc.checks["database"] == "healthy"
