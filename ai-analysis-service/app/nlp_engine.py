"""
NLP similarity engine using TF-IDF + cosine similarity.

Compares incoming alert messages against:
  1. A static knowledge base of known SRE patterns
  2. Historical resolved incidents from the database

No heavy ML models — runs on pure scikit-learn, startup is instant.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from app.knowledge_base import KNOWN_PATTERNS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

# ── helpers ──────────────────────────────────────────────────

_NOISE_RE = re.compile(r"[^a-z0-9\s]+")
_MULTI_SPACE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace."""
    t = text.lower()
    t = _NOISE_RE.sub(" ", t)
    return _MULTI_SPACE.sub(" ", t).strip()


# ── data classes ─────────────────────────────────────────────


@dataclass
class Suggestion:
    root_cause: str
    solution: str
    confidence: float
    source: str  # "knowledge_base" | "historical"
    matched_pattern: str


@dataclass
class HistoricalEntry:
    incident_id: int
    service: str
    severity: str
    title: str
    description: str
    notes: list[str] = field(default_factory=list)
    resolution: str = ""


# ── engine ───────────────────────────────────────────────────


class SimilarityEngine:
    """
    Maintains a TF-IDF index over knowledge-base patterns and historical
    incidents.  Call ``analyse()`` with a raw alert message to get ranked
    suggestions.
    """

    def __init__(self, min_confidence: float = 0.12):
        self.min_confidence = min_confidence

        # build static corpus from knowledge base
        self._kb_docs: list[str] = []
        self._kb_entries: list[dict] = []
        for entry in KNOWN_PATTERNS:
            self._kb_docs.append(_normalise(entry["pattern"]))
            self._kb_entries.append(entry)

        # historical corpus (populated from DB)
        self._hist_docs: list[str] = []
        self._hist_entries: list[HistoricalEntry] = []

        # vectoriser + matrix will be (re)built on first call / refresh
        self._vectoriser: Optional[TfidfVectorizer] = None
        self._tfidf_matrix = None
        self._corpus_size = 0

        self._build_index()
        logger.info(
            "SimilarityEngine initialised with %d knowledge-base patterns",
            len(self._kb_docs),
        )

    # ── public API ───────────────────────────────────────────

    def analyse(
        self,
        alert_message: str,
        alert_service: str | None = None,
        top_k: int = 5,
    ) -> list[Suggestion]:
        """Return up to *top_k* suggestions for the given alert text."""
        if self._vectoriser is None or self._tfidf_matrix is None:
            self._build_index()

        query = _normalise(alert_message)
        if not query:
            return []

        query_vec = self._vectoriser.transform([query])
        scores = cosine_similarity(query_vec, self._tfidf_matrix).flatten()

        kb_len = len(self._kb_docs)
        suggestions: list[Suggestion] = []

        ranked_idxs = np.argsort(scores)[::-1]
        for idx in ranked_idxs:
            score = float(scores[idx])
            if score < self.min_confidence:
                continue

            if idx < kb_len:
                entry = self._kb_entries[idx]
                # optional boost if service matches the hint
                if (
                    alert_service
                    and entry.get("service_hint")
                    and alert_service.lower() in entry["service_hint"].lower()
                ):
                    score = min(score * 1.15, 1.0)

                suggestions.append(
                    Suggestion(
                        root_cause=entry["root_cause"],
                        solution=entry["solution"],
                        confidence=round(score, 4),
                        source="knowledge_base",
                        matched_pattern=entry["pattern"][:120],
                    )
                )
            else:
                hist_idx = idx - kb_len
                if hist_idx < len(self._hist_entries):
                    hist = self._hist_entries[hist_idx]
                    resolution_text = hist.resolution or "See incident notes for resolution details."
                    root_cause = f"Similar to historical incident #{hist.incident_id}: {hist.title}"
                    suggestions.append(
                        Suggestion(
                            root_cause=root_cause,
                            solution=resolution_text,
                            confidence=round(score, 4),
                            source="historical",
                            matched_pattern=f"incident #{hist.incident_id}",
                        )
                    )

            if len(suggestions) >= top_k:
                break

        return suggestions

    def load_historical(self, entries: list[HistoricalEntry]) -> None:
        """Replace the historical corpus and rebuild the index."""
        self._hist_docs = []
        self._hist_entries = []
        for e in entries:
            doc = _normalise(f"{e.title} {e.description} {e.service} {e.severity} " + " ".join(e.notes))
            self._hist_docs.append(doc)
            self._hist_entries.append(e)

        self._build_index()
        logger.info(
            "Loaded %d historical entries, total corpus = %d",
            len(entries),
            self._corpus_size,
        )

    # ── internal ─────────────────────────────────────────────

    def _build_index(self) -> None:
        corpus = self._kb_docs + self._hist_docs
        if not corpus:
            return
        self._vectoriser = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=5000,
        )
        self._tfidf_matrix = self._vectoriser.fit_transform(corpus)
        self._corpus_size = len(corpus)
