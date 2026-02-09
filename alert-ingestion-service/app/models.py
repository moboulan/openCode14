from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime, timezone
from enum import Enum

class SeverityLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class IncidentStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"

class Alert(BaseModel):
    """Alert model"""
    service: str = Field(..., description="Service name that generated the alert")
    severity: SeverityLevel = Field(..., description="Alert severity level")
    message: str = Field(..., description="Alert message")
    labels: Optional[Dict[str, str]] = Field(default_factory=dict, description="Additional labels")
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc), description="Alert timestamp")

class AlertResponse(BaseModel):
    """Alert response model"""
    alert_id: str
    incident_id: Optional[str] = None
    status: str
    action: str
    timestamp: datetime

class Incident(BaseModel):
    """Incident model"""
    incident_id: str
    title: str
    service: str
    severity: SeverityLevel
    status: IncidentStatus
    assigned_to: Optional[str] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    notes: List[str] = Field(default_factory=list)

class HealthCheck(BaseModel):
    """Health check response model"""
    status: str
    timestamp: datetime
    service: str
    version: str
    uptime: float
    checks: Dict[str, str]
