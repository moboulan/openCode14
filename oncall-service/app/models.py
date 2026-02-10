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
    handoff_hour: int = Field(default=9, ge=0, le=23, description="Hour of day for rotation handoff (0-23)")
    timezone: str = Field(default="UTC", description="Schedule timezone (e.g. UTC, US/Eastern)")


class EscalateRequest(BaseModel):
    """Request to escalate an incident to secondary on-call."""

    incident_id: str = Field(..., description="Incident ID to escalate")
    team: Optional[str] = Field(None, description="Team to escalate within (optional)")
    reason: Optional[str] = Field(None, description="Reason for escalation")
    level: Optional[int] = Field(None, ge=1, description="Escalation level (auto-determined if omitted)")


# ---------------------------------------------------------------------------
# Escalation Policy models
# ---------------------------------------------------------------------------


class EscalationPolicyLevel(BaseModel):
    """A single level in an escalation policy."""

    level: int = Field(..., ge=1, description="Escalation level (1 = first escalation)")
    wait_minutes: int = Field(..., ge=1, description="Minutes to wait before escalating to this level")
    notify_target: str = Field(..., description="Target: 'secondary', 'manager', or an email")


class EscalationPolicyCreateRequest(BaseModel):
    """Create or replace escalation policy for a team."""

    team: str = Field(..., description="Team name")
    levels: List[EscalationPolicyLevel] = Field(..., min_length=1, description="Ordered escalation levels")


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
    handoff_hour: int = 9
    timezone: str = "UTC"
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
    handoff_hour: int = 9
    timezone: str = "UTC"


class EscalateResponse(BaseModel):
    """Response after escalating an incident."""

    escalation_id: str
    incident_id: str
    from_engineer: str
    to_engineer: str
    level: int = 1
    reason: Optional[str]
    escalated_at: datetime


class EscalationHistoryItem(BaseModel):
    """Single escalation record."""

    id: str
    incident_id: str
    from_engineer: str
    to_engineer: str
    level: int = 1
    reason: Optional[str]
    escalated_at: datetime


class EscalationPolicyResponse(BaseModel):
    """Escalation policy for a team."""

    team: str
    levels: List[EscalationPolicyLevel]


class EscalationTimerResponse(BaseModel):
    """Active escalation timer."""

    id: str
    incident_id: str
    team: str
    current_level: int
    assigned_to: str
    escalate_after: datetime
    is_active: bool


class AutoEscalationResult(BaseModel):
    """Result of running the automatic escalation check."""

    checked: int
    escalated: int
    details: List[Dict]


# ---------------------------------------------------------------------------
# Timer management models (for incident-management integration)
# ---------------------------------------------------------------------------


class TimerStartRequest(BaseModel):
    """Start an escalation timer for a newly assigned incident."""

    incident_id: str = Field(..., description="Incident ID to track")
    team: str = Field(..., description="Team responsible for the incident")
    assigned_to: str = Field(..., description="Currently assigned engineer (name or email)")


class TimerCancelRequest(BaseModel):
    """Cancel active escalation timer(s) for an incident."""

    incident_id: str = Field(..., description="Incident ID whose timer(s) to cancel")


class TimerStartResponse(BaseModel):
    """Response after starting an escalation timer."""

    timer_id: str
    incident_id: str
    team: str
    assigned_to: str
    escalate_after: datetime
    current_level: int


class TimerCancelResponse(BaseModel):
    """Response after cancelling escalation timer(s)."""

    incident_id: str
    cancelled_count: int


class TimerListResponse(BaseModel):
    """List of active escalation timers."""

    timers: List[EscalationTimerResponse]
    total: int


# ---------------------------------------------------------------------------
# Schedule member models
# ---------------------------------------------------------------------------


class ScheduleMemberCreate(BaseModel):
    """Add a member to a schedule rotation."""

    user_name: str = Field(..., description="Engineer display name")
    user_email: str = Field(..., description="Engineer email address")
    position: int = Field(..., ge=1, description="Position in rotation (1-based)")


class ScheduleMemberResponse(BaseModel):
    """A member in a schedule rotation."""

    id: str
    schedule_id: str
    user_name: str
    user_email: str
    position: int
    is_active: bool = True
    created_at: datetime


class ScheduleMemberListResponse(BaseModel):
    """List of schedule members."""

    members: List[ScheduleMemberResponse]
    total: int


# ---------------------------------------------------------------------------
# Analytics / Metrics models
# ---------------------------------------------------------------------------


class OnCallMetrics(BaseModel):
    """Key on-call metrics: MTTA, MTTR, escalation rate, on-call load."""

    total_incidents: int = 0
    total_escalations: int = 0
    escalation_rate_pct: Optional[float] = None
    avg_mtta_seconds: Optional[float] = None
    avg_mttr_seconds: Optional[float] = None
    oncall_load: Dict[str, int] = Field(default_factory=dict)
    by_team: Dict[str, int] = Field(default_factory=dict)


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
