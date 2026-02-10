"""Tests for Pydantic models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models import (
    HealthCheck,
    IncidentAnalyticsResponse,
    IncidentCreate,
    IncidentMetrics,
    IncidentResponse,
    IncidentStatus,
    IncidentUpdate,
    SeverityLevel,
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
        expected = {
            "open",
            "acknowledged",
            "in_progress",
            "investigating",
            "mitigated",
            "resolved",
            "closed",
        }
        assert {s.value for s in IncidentStatus} == expected


# ── IncidentCreate model ─────────────────────────────────────


class TestIncidentCreate:
    def test_valid_minimal(self):
        m = IncidentCreate(title="Outage", service="web", severity="critical")
        assert m.title == "Outage"
        assert m.severity == SeverityLevel.CRITICAL
        assert m.description is None

    def test_valid_full(self):
        m = IncidentCreate(
            title="High latency",
            service="api-gateway",
            severity="low",
            description="P99 > 5s",
        )
        assert m.description == "P99 > 5s"

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValidationError):
            IncidentCreate(title="X", service="x", severity="INVALID")

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            IncidentCreate(title="X")  # missing service, severity


# ── IncidentUpdate model ─────────────────────────────────────


class TestIncidentUpdate:
    def test_all_none_valid(self):
        m = IncidentUpdate()
        assert m.status is None
        assert m.assigned_to is None
        assert m.note is None

    def test_status_only(self):
        m = IncidentUpdate(status="acknowledged")
        assert m.status == IncidentStatus.ACKNOWLEDGED

    def test_note_only(self):
        m = IncidentUpdate(note="investigating root cause")
        assert m.note == "investigating root cause"


# ── IncidentResponse model ───────────────────────────────────


class TestIncidentResponse:
    def test_valid_response(self):
        r = IncidentResponse(
            incident_id="inc-abc123",
            title="Test",
            service="web",
            severity="high",
            status="open",
            created_at=datetime.now(timezone.utc),
        )
        assert r.incident_id == "inc-abc123"
        assert r.notes == []
        assert r.acknowledged_at is None


# ── IncidentMetrics model ────────────────────────────────────


class TestIncidentMetrics:
    def test_not_yet_resolved(self):
        m = IncidentMetrics(incident_id="inc-1", status="open")
        assert m.mtta_seconds is None
        assert m.mttr_seconds is None

    def test_with_values(self):
        m = IncidentMetrics(
            incident_id="inc-2",
            mtta_seconds=45.0,
            mttr_seconds=1800.0,
            status="resolved",
        )
        assert m.mtta_seconds == 45.0
        assert m.mttr_seconds == 1800.0


# ── IncidentAnalyticsResponse model ──────────────────────────


class TestIncidentAnalyticsResponse:
    def test_defaults(self):
        a = IncidentAnalyticsResponse()
        assert a.total_incidents == 0
        assert a.by_severity == {}
        assert a.avg_mtta_seconds is None


# ── HealthCheck model ────────────────────────────────────────


class TestHealthCheckModel:
    def test_valid_health_check(self):
        hc = HealthCheck(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            service="incident-management",
            version="1.0.0",
            uptime=123.45,
            checks={"database": "healthy", "memory": "healthy"},
        )
        assert hc.status == "healthy"
        assert hc.uptime == 123.45
        assert hc.checks["database"] == "healthy"
