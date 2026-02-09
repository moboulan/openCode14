"""Tests for app/models.py -- Pydantic model validation."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from app.models import (
    CurrentOnCallResponse,
    Engineer,
    EscalateRequest,
    EscalateResponse,
    OnCallEngineer,
    ScheduleCreateRequest,
    ScheduleListResponse,
    ScheduleResponse,
)


def test_engineer_model():
    """Engineer model validates correctly."""
    eng = Engineer(name="Alice", email="alice@example.com", primary=True)
    assert eng.name == "Alice"
    assert eng.primary is True


def test_schedule_create_request():
    """ScheduleCreateRequest validates correctly."""
    req = ScheduleCreateRequest(
        team="platform",
        rotation_type="weekly",
        start_date="2026-01-01",
        engineers=[
            Engineer(name="Alice", email="alice@example.com", primary=True),
        ],
        escalation_minutes=5,
    )
    assert req.team == "platform"
    assert len(req.engineers) == 1


def test_schedule_create_requires_engineers():
    """ScheduleCreateRequest requires at least one engineer."""
    with pytest.raises(ValidationError):
        ScheduleCreateRequest(
            team="platform",
            rotation_type="weekly",
            start_date="2026-01-01",
            engineers=[],
            escalation_minutes=5,
        )


def test_escalate_request():
    """EscalateRequest validates correctly."""
    req = EscalateRequest(incident_id="inc-123", team="platform")
    assert req.incident_id == "inc-123"
    assert req.reason is None


def test_schedule_response():
    """ScheduleResponse serializes correctly."""
    resp = ScheduleResponse(
        id="sched-1",
        team="platform",
        rotation_type="weekly",
        start_date=date(2026, 1, 1),
        engineers=[Engineer(name="Alice", email="alice@example.com", primary=True)],
        escalation_minutes=5,
        created_at=datetime(2026, 1, 1),
    )
    assert resp.team == "platform"


def test_current_oncall_response():
    """CurrentOnCallResponse serializes correctly."""
    resp = CurrentOnCallResponse(
        team="platform",
        primary=OnCallEngineer(name="Alice", email="alice@example.com", role="primary"),
        secondary=OnCallEngineer(name="Bob", email="bob@example.com", role="secondary"),
        schedule_id="sched-1",
        rotation_type="weekly",
        escalation_minutes=5,
    )
    assert resp.primary.name == "Alice"
    assert resp.secondary.name == "Bob"


def test_current_oncall_response_no_secondary():
    """CurrentOnCallResponse works without secondary."""
    resp = CurrentOnCallResponse(
        team="solo",
        primary=OnCallEngineer(name="Alice", email="alice@example.com", role="primary"),
        schedule_id="sched-1",
        rotation_type="daily",
        escalation_minutes=10,
    )
    assert resp.secondary is None
