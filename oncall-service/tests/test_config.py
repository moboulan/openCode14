"""Tests for app/config.py -- Settings."""

import os
from unittest.mock import patch

import pytest


def test_settings_loads_defaults():
    """Settings loads with defaults when DATABASE_URL is set."""
    from app.config import settings

    assert settings.SERVICE_NAME == "oncall-service"
    assert settings.SERVICE_PORT == 8003
    assert settings.APP_VERSION == "1.0.0"
    assert settings.DB_POOL_MIN == 1
    assert settings.DB_POOL_MAX == 10
    assert settings.DEFAULT_ESCALATION_MINUTES == 5
    assert settings.MANAGER_EMAIL == "admin@expertmind.local"
    assert settings.ESCALATION_LOOP_COUNT == 2


def test_settings_cors_origin_list():
    """cors_origin_list splits CORS_ORIGINS."""
    from app.config import settings

    origins = settings.cors_origin_list
    assert isinstance(origins, list)
    assert len(origins) >= 1
    assert "http://localhost:8080" in origins


def test_settings_requires_database_url():
    """Settings requires DATABASE_URL to be set."""
    env = os.environ.copy()
    env.pop("DATABASE_URL", None)

    with patch.dict(os.environ, env, clear=True):
        from pydantic import ValidationError  # noqa: F401

        with pytest.raises((ValidationError, Exception)):
            from importlib import reload

            import app.config

            reload(app.config)
