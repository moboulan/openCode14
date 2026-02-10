"""
AI Analysis Service – main FastAPI application.

Runs a TF-IDF-based similarity engine that compares incoming alerts against a
static knowledge base of SRE patterns *and* historical resolved incidents
fetched from the database.

The historical corpus is refreshed periodically in the background.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from app.config import settings
from app.database import (check_database_health, close_pool, get_db_connection,
                          init_pool)
from app.knowledge_base import KNOWN_PATTERNS
from app.models import HealthCheck
from app.nlp_engine import HistoricalEntry, SimilarityEngine
from app.routers import api as api_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

engine: SimilarityEngine | None = None
_refresh_task: asyncio.Task | None = None


# ── historical refresh ───────────────────────────────────────


def _fetch_historical_from_db() -> list[HistoricalEntry]:
    """Query resolved incidents directly from the database."""
    entries: list[HistoricalEntry] = []
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT incident_id, title, description, service, severity,
                           status, notes, assigned_to
                    FROM incidents.incidents
                    WHERE status IN ('resolved', 'closed', 'mitigated')
                    ORDER BY resolved_at DESC NULLS LAST
                    LIMIT 500
                    """
                )
                for row in cur.fetchall():
                    notes_list = []
                    if row[6]:  # notes is JSONB array
                        for n in row[6]:
                            if isinstance(n, dict):
                                notes_list.append(n.get("content", ""))
                            elif isinstance(n, str):
                                notes_list.append(n)

                    resolution = ""
                    if notes_list:
                        resolution = notes_list[-1]  # last note is usually resolution

                    entries.append(
                        HistoricalEntry(
                            incident_id=row[0],
                            title=row[1] or "",
                            description=row[2] or "",
                            service=row[3] or "",
                            severity=row[4] or "",
                            notes=notes_list,
                            resolution=resolution,
                        )
                    )
    except Exception:
        logger.exception("Failed to fetch historical incidents")
    return entries


async def _periodic_refresh():
    """Background loop that refreshes the historical corpus."""
    while True:
        try:
            await asyncio.sleep(settings.HISTORICAL_REFRESH_INTERVAL)
            entries = await asyncio.to_thread(_fetch_historical_from_db)
            if engine:
                engine.load_historical(entries)
                logger.info("Refreshed historical corpus: %d entries", len(entries))
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in periodic refresh")


# ── lifespan ─────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, _refresh_task

    # startup
    init_pool()
    engine = SimilarityEngine(min_confidence=settings.MIN_CONFIDENCE)
    api_router.set_engine(engine)

    # initial historical load
    entries = await asyncio.to_thread(_fetch_historical_from_db)
    engine.load_historical(entries)
    logger.info("Initial historical load: %d entries", len(entries))

    _refresh_task = asyncio.create_task(_periodic_refresh())
    logger.info("AI Analysis Service started on port %d", settings.SERVICE_PORT)

    yield

    # shutdown
    if _refresh_task:
        _refresh_task.cancel()
        try:
            await _refresh_task
        except asyncio.CancelledError:
            pass
    close_pool()
    logger.info("AI Analysis Service stopped")


# ── app ──────────────────────────────────────────────────────

app = FastAPI(
    title="AI Analysis Service",
    description="NLP-powered alert analysis with root-cause suggestions",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

app.include_router(api_router.router)


# ── health ───────────────────────────────────────────────────


@app.get("/health", response_model=HealthCheck)
async def health():
    db_ok = check_database_health()
    return HealthCheck(
        status="healthy" if db_ok else "degraded",
        corpus_size=engine._corpus_size if engine else 0,
        knowledge_base_patterns=len(KNOWN_PATTERNS),
        historical_entries=len(engine._hist_entries) if engine else 0,
    )
