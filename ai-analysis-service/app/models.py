"""Pydantic models for the AI analysis service."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


# ── Request models ───────────────────────────────────────────


class AnalyseRequest(BaseModel):
    """Payload sent by alert-ingestion (or manually) to trigger analysis."""

    alert_id: Optional[str] = None
    incident_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    service: Optional[str] = None
    severity: Optional[str] = None


# ── Response models ──────────────────────────────────────────


class SuggestionResponse(BaseModel):
    root_cause: str
    solution: str
    confidence: float
    source: str
    matched_pattern: Optional[str] = None


class AnalysisResponse(BaseModel):
    alert_id: Optional[str] = None
    incident_id: Optional[str] = None
    suggestions: list[SuggestionResponse]
    analysed_at: datetime


class HealthCheck(BaseModel):
    status: str
    service: str = "ai-analysis-service"
    corpus_size: int = 0
    knowledge_base_patterns: int = 0
    historical_entries: int = 0
