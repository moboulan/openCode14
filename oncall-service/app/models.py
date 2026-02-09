from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RotationType(str, Enum):
    WEEKLY = "weekly"
    DAILY = "daily"


class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ---------------------------------------------------------------------------
# Engineer sub-model (stored as JSONB in schedules.engineers)
# ---------------------------------------------------------------------------


class Engineer(BaseModel):
    name: str
    email: str
    primary: bool = False


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class ScheduleCreateRequest(BaseModel):
    """Create a new on-call rotation schedule."""

    team: str = Field(..., description="Team name (e.g. platform, backend, frontend)")
    rotation_type: RotationType = Field(default=RotationType.WEEKLY, description="Rotation type")
    start_date: date = Field(..., description="Rotation start date")
    engineers: List[Engineer] = Field(..., min_length=1, description="Ordered list of engineers in rotation")
    escalation_minutes: int = Field(default=5, ge=1, description="Minutes before escalation")


class EscalateRequest(BaseModel):
    """Request to escalate an incident to secondary on-call."""

    incident_id: str = Field(..., description="Incident ID to escalate")
    team: Optional[str] = Field(None, description="Team to escalate within (optional)")
    reason: Optional[str] = Field(None, description="Reason for escalation")


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class ScheduleResponse(BaseModel):
    """A single on-call schedule."""

    id: str
    team: str
    rotation_type: str
    start_date: date
    engineers: List[Engineer]
    escalation_minutes: int
    created_at: datetime


class ScheduleListResponse(BaseModel):
    """List of schedules."""

    schedules: List[ScheduleResponse]
    total: int


class OnCallEngineer(BaseModel):
    """Current on-call engineer info."""

    name: str
    email: str
    role: str = "primary"


class CurrentOnCallResponse(BaseModel):
    """Current on-call response for a team."""

    team: str
    primary: OnCallEngineer
    secondary: Optional[OnCallEngineer] = None
    schedule_id: str
    rotation_type: str
    escalation_minutes: int


class EscalateResponse(BaseModel):
    """Response after escalating an incident."""

    escalation_id: str
    incident_id: str
    from_engineer: str
    to_engineer: str
    reason: Optional[str]
    escalated_at: datetime


class EscalationHistoryItem(BaseModel):
    """Single escalation record."""

    id: str
    incident_id: str
    from_engineer: str
    to_engineer: str
    reason: Optional[str]
    escalated_at: datetime


# ---------------------------------------------------------------------------
# Shared models
# ---------------------------------------------------------------------------


class HealthCheck(BaseModel):
    """Health check response model"""

    status: str
    timestamp: datetime
    service: str
    version: str
    uptime: float
    checks: Dict[str, str]
