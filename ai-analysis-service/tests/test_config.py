"""Tests for app.config module."""

import os
from unittest.mock import patch


def test_default_settings():
    """Settings has sane defaults."""
    from app.config import Settings

    s = Settings()
    assert s.SERVICE_PORT == 8005
    assert s.MIN_CONFIDENCE == 0.12
    assert s.TOP_K_SUGGESTIONS == 5
    assert s.HISTORICAL_REFRESH_INTERVAL == 300


def test_settings_override_from_env():
    """Settings can be overridden via environment variables."""
    with patch.dict(os.environ, {"MIN_CONFIDENCE": "0.5", "TOP_K_SUGGESTIONS": "10"}):
        from pydantic_settings import BaseSettings  # noqa: F401

        from app.config import Settings

        s = Settings()
        assert s.MIN_CONFIDENCE == 0.5
        assert s.TOP_K_SUGGESTIONS == 10
