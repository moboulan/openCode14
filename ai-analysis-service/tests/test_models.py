"""Tests for Pydantic models."""

from datetime import datetime, timezone

import pytest
from app.models import (
    AnalyseRequest,
    AnalysisResponse,
    HealthCheck,
    SeverityLevel,
    SuggestionResponse,
)
from pydantic import ValidationError


class TestAnalyseRequest:
    def test_valid_full(self):
        req = AnalyseRequest(
            alert_id="a-1",
            incident_id="i-2",
            message="test alert",
            service="svc",
            severity="critical",
        )
        assert req.message == "test alert"
        assert req.alert_id == "a-1"

    def test_valid_minimal(self):
        req = AnalyseRequest(message="some alert text")
        assert req.alert_id is None
        assert req.incident_id is None
        assert req.service is None

    def test_empty_message_rejected(self):
        with pytest.raises(ValidationError):
            AnalyseRequest(message="")

    def test_missing_message_rejected(self):
        with pytest.raises(ValidationError):
            AnalyseRequest()


class TestSuggestionResponse:
    def test_valid(self):
        s = SuggestionResponse(
            root_cause="CPU overload",
            solution="Scale pods",
            confidence=0.91,
            source="knowledge_base",
            matched_pattern="cpu usage high",
        )
        assert s.confidence == 0.91

    def test_optional_matched_pattern(self):
        s = SuggestionResponse(
            root_cause="Unknown",
            solution="Investigate",
            confidence=0.5,
            source="historical",
        )
        assert s.matched_pattern is None


class TestAnalysisResponse:
    def test_valid(self):
        resp = AnalysisResponse(
            alert_id="a-1",
            incident_id="i-2",
            suggestions=[],
            analysed_at=datetime.now(timezone.utc),
        )
        assert resp.suggestions == []

    def test_with_suggestions(self):
        sugg = SuggestionResponse(
            root_cause="Disk full",
            solution="Expand volume",
            confidence=0.88,
            source="knowledge_base",
        )
        resp = AnalysisResponse(
            suggestions=[sugg],
            analysed_at=datetime.now(timezone.utc),
        )
        assert len(resp.suggestions) == 1


class TestHealthCheck:
    def test_defaults(self):
        hc = HealthCheck(status="healthy")
        assert hc.service == "ai-analysis-service"
        assert hc.corpus_size == 0


class TestSeverityLevel:
    def test_valid_values(self):
        assert SeverityLevel.critical == "critical"
        assert SeverityLevel.high == "high"
        assert SeverityLevel.info == "info"
