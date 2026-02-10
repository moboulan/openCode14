"""
API router for the AI analysis service.

Endpoints:
    POST /api/v1/analyze           – analyse an alert and return suggestions
    GET  /api/v1/suggestions       – list stored suggestions (by alert or incident)
    GET  /api/v1/knowledge-base    – list static knowledge-base patterns
    POST /api/v1/learn             – store a resolved pattern for future matching
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.database import get_db_connection
from app.knowledge_base import KNOWN_PATTERNS
from app.models import (
    AnalyseRequest,
    AnalysisResponse,
    SuggestionResponse,
)
from app.nlp_engine import SimilarityEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["analysis"])

# The engine is injected from main.py at startup
engine: SimilarityEngine | None = None


def set_engine(e: SimilarityEngine) -> None:
    global engine
    engine = e


# ── POST /analyze ────────────────────────────────────────────


@router.post("/analyze", response_model=AnalysisResponse)
async def analyse_alert(req: AnalyseRequest):
    """Run NLP similarity analysis on the given alert message."""
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")

    results = engine.analyse(
        alert_message=req.message,
        alert_service=req.service,
        top_k=settings.TOP_K_SUGGESTIONS,
    )

    suggestions = [
        SuggestionResponse(
            root_cause=s.root_cause,
            solution=s.solution,
            confidence=s.confidence,
            source=s.source,
            matched_pattern=s.matched_pattern,
        )
        for s in results
    ]

    # persist so the web UI can fetch them later
    if suggestions:
        _store_suggestions(req, suggestions)

    return AnalysisResponse(
        alert_id=req.alert_id,
        incident_id=req.incident_id,
        suggestions=suggestions,
        analysed_at=datetime.now(timezone.utc),
    )


def _store_suggestions(req: AnalyseRequest, suggestions: list[SuggestionResponse]):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                for s in suggestions:
                    cur.execute(
                        """
                        INSERT INTO analysis.suggestions
                            (alert_id, incident_id, alert_message, alert_service, alert_severity,
                             root_cause, solution, confidence, source, matched_pattern)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            req.alert_id,
                            req.incident_id,
                            req.message[:500],
                            req.service,
                            req.severity,
                            s.root_cause,
                            s.solution,
                            s.confidence,
                            s.source,
                            s.matched_pattern,
                        ),
                    )
    except Exception:
        logger.exception("Failed to persist suggestions")


# ── GET /suggestions ─────────────────────────────────────────


@router.get("/suggestions", response_model=list[SuggestionResponse])
async def list_suggestions(
    alert_id: str | None = Query(None),
    incident_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    """Retrieve previously-stored suggestions by alert or incident."""
    if alert_id is None and incident_id is None:
        raise HTTPException(400, "Provide alert_id or incident_id")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if incident_id is not None:
                    cur.execute(
                        """
                        SELECT root_cause, solution, confidence, source, matched_pattern
                        FROM analysis.suggestions
                        WHERE incident_id = %s
                        ORDER BY confidence DESC
                        LIMIT %s
                        """,
                        (incident_id, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT root_cause, solution, confidence, source, matched_pattern
                        FROM analysis.suggestions
                        WHERE alert_id = %s
                        ORDER BY confidence DESC
                        LIMIT %s
                        """,
                        (alert_id, limit),
                    )
                rows = cur.fetchall()
    except Exception:
        logger.exception("DB error fetching suggestions")
        raise HTTPException(500, "Database error")

    return [
        SuggestionResponse(
            root_cause=r[0],
            solution=r[1],
            confidence=r[2],
            source=r[3],
            matched_pattern=r[4],
        )
        for r in rows
    ]


# ── GET /knowledge-base ─────────────────────────────────────


@router.get("/knowledge-base")
async def list_knowledge_base():
    """Return the static knowledge-base patterns."""
    return [
        {
            "pattern": entry["pattern"],
            "root_cause": entry["root_cause"],
            "solution": entry["solution"],
            "tags": entry.get("tags", []),
        }
        for entry in KNOWN_PATTERNS
    ]


# ── POST /learn ─────────────────────────────────────────────


@router.post("/learn", status_code=201)
async def learn_pattern(
    service: str | None = None,
    severity: str | None = None,
    message_pattern: str = "",
    root_cause: str = "",
    solution: str = "",
):
    """Store a resolved pattern so future alerts can match it."""
    if not message_pattern or not root_cause:
        raise HTTPException(400, "message_pattern and root_cause are required")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analysis.resolved_patterns
                        (service, severity, message_pattern, root_cause, solution)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING pattern_id
                    """,
                    (service, severity, message_pattern, root_cause, solution),
                )
                pid = cur.fetchone()[0]
    except Exception:
        logger.exception("Failed to store learned pattern")
        raise HTTPException(500, "Database error")

    return {"pattern_id": pid, "status": "learned"}
