"""Tests for the knowledge_base module."""

from app.knowledge_base import KNOWN_PATTERNS


class TestKnowledgeBase:
    """Verify the static knowledge base is well-formed."""

    def test_patterns_not_empty(self):
        assert len(KNOWN_PATTERNS) > 0

    def test_each_pattern_has_required_keys(self):
        required = {"pattern", "root_cause", "solution", "tags"}
        for i, entry in enumerate(KNOWN_PATTERNS):
            for key in required:
                assert key in entry, f"Entry {i} is missing key '{key}'"

    def test_pattern_is_nonempty_string(self):
        for entry in KNOWN_PATTERNS:
            assert isinstance(entry["pattern"], str)
            assert len(entry["pattern"]) > 0

    def test_tags_are_list(self):
        for entry in KNOWN_PATTERNS:
            assert isinstance(entry["tags"], list)

    def test_no_duplicate_patterns(self):
        patterns = [e["pattern"] for e in KNOWN_PATTERNS]
        assert len(patterns) == len(set(patterns)), "Duplicate patterns found"

    def test_minimum_pattern_count(self):
        """We should have at least 10 patterns in the knowledge base."""
        assert len(KNOWN_PATTERNS) >= 10
