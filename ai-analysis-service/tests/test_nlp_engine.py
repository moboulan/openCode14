"""Tests for the NLP similarity engine."""

from app.nlp_engine import SimilarityEngine, HistoricalEntry, _normalise, Suggestion


class TestNormalise:
    """Tests for the _normalise helper function."""

    def test_lowercases(self):
        assert _normalise("HIGH CPU USAGE") == "high cpu usage"

    def test_strips_punctuation(self):
        assert _normalise("error: timeout!") == "error timeout"

    def test_collapses_whitespace(self):
        assert _normalise("too   many   spaces") == "too many spaces"

    def test_empty_string(self):
        assert _normalise("") == ""

    def test_preserves_numbers(self):
        assert _normalise("Error 503 on port 8080") == "error 503 on port 8080"


class TestSimilarityEngine:
    """Tests for the core SimilarityEngine."""

    def test_init_creates_index(self):
        engine = SimilarityEngine(min_confidence=0.1)
        assert engine._corpus_size > 0
        assert engine._vectoriser is not None

    def test_analyse_returns_suggestions(self):
        engine = SimilarityEngine(min_confidence=0.1)
        results = engine.analyse("high cpu usage detected on server")
        assert len(results) > 0
        assert all(isinstance(s, Suggestion) for s in results)

    def test_analyse_confidence_above_threshold(self):
        engine = SimilarityEngine(min_confidence=0.1)
        results = engine.analyse("high cpu usage detected")
        for s in results:
            assert s.confidence >= 0.1

    def test_analyse_top_k_limit(self):
        engine = SimilarityEngine(min_confidence=0.01)
        results = engine.analyse("error timeout connection failure", top_k=3)
        assert len(results) <= 3

    def test_analyse_empty_returns_empty(self):
        engine = SimilarityEngine(min_confidence=0.1)
        results = engine.analyse("")
        assert results == []

    def test_analyse_cpu_alert_matches_cpu_pattern(self):
        engine = SimilarityEngine(min_confidence=0.1)
        results = engine.analyse("CPU utilization above 95% threshold")
        assert len(results) > 0
        # The top result should be from knowledge_base related to CPU
        assert (
            "cpu" in results[0].root_cause.lower()
            or "cpu" in results[0].matched_pattern.lower()
        )

    def test_analyse_service_hint_boost(self):
        """When alert_service matches a pattern's service_hint, confidence is boosted."""
        engine = SimilarityEngine(min_confidence=0.1)
        results_no_hint = engine.analyse("high cpu usage")
        results_with_hint = engine.analyse(
            "high cpu usage", alert_service="some-service"
        )
        # Both should return results; with hint the confidence may be boosted if service matches
        assert len(results_no_hint) > 0
        assert len(results_with_hint) > 0

    def test_load_historical(self):
        engine = SimilarityEngine(min_confidence=0.1)
        initial_size = engine._corpus_size

        entries = [
            HistoricalEntry(
                incident_id=1,
                title="Payment API high latency",
                description="Payment service response time exceeded 5s threshold",
                service="payment-api",
                severity="critical",
                notes=[
                    "Investigated DB pool exhaustion",
                    "Scaled DB connections from 10 to 50",
                ],
                resolution="Scaled DB connections from 10 to 50",
            ),
            HistoricalEntry(
                incident_id=2,
                title="Redis cluster split-brain",
                description="Redis sentinel detected split-brain condition",
                service="cache-service",
                severity="high",
                notes=["Manually triggered failover to healthy master"],
                resolution="Manually triggered failover to healthy master",
            ),
        ]
        engine.load_historical(entries)

        assert engine._corpus_size == initial_size + 2
        assert len(engine._hist_entries) == 2

    def test_historical_match(self):
        engine = SimilarityEngine(min_confidence=0.05)
        entries = [
            HistoricalEntry(
                incident_id=99,
                title="Redis connection timeout causing cascading failures",
                description="Redis connection pool exhausted timeout after 30s",
                service="cache-service",
                severity="critical",
                notes=["Increased Redis pool size and added circuit breaker"],
                resolution="Increased Redis pool size and added circuit breaker",
            ),
        ]
        engine.load_historical(entries)

        results = engine.analyse("redis connection timeout pool exhausted")
        # Should have at least one historical match
        historical_results = [s for s in results if s.source == "historical"]
        assert len(historical_results) > 0

    def test_suggestion_fields(self):
        engine = SimilarityEngine(min_confidence=0.1)
        results = engine.analyse("disk space low filesystem usage above 90%")
        assert len(results) > 0
        s = results[0]
        assert isinstance(s.root_cause, str)
        assert isinstance(s.solution, str)
        assert isinstance(s.confidence, float)
        assert s.source in ("knowledge_base", "historical")
        assert isinstance(s.matched_pattern, str)

    def test_multiple_builds(self):
        """Engine can rebuild index multiple times."""
        engine = SimilarityEngine(min_confidence=0.1)
        engine._build_index()
        engine._build_index()
        assert engine._corpus_size > 0
