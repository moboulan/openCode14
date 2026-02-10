"""Tests for the notification service configuration."""

import os
from unittest.mock import patch


def test_settings_defaults():
    """Settings should have correct defaults for notification service."""
    with patch.dict(
        os.environ,
        {"DATABASE_URL": "postgresql://test:test@localhost/test"},
        clear=False,
    ):
        # Force reimport to pick up env
        import importlib

        import app.config

        importlib.reload(app.config)

        s = app.config.Settings(DATABASE_URL="postgresql://test:test@localhost/test")
        assert s.SERVICE_NAME == "notification-service"
        assert s.SERVICE_PORT == 8004
        assert s.APP_VERSION == "1.0.0"
        assert s.ENVIRONMENT == "development"
        assert s.DB_POOL_MIN == 1
        assert s.DB_POOL_MAX == 10


def test_cors_origin_list():
    """cors_origin_list should split comma-separated origins."""
    from app.config import Settings

    s = Settings(
        DATABASE_URL="postgresql://x@localhost/x",
        CORS_ORIGINS="http://a.com, http://b.com ,http://c.com",
    )
    assert s.cors_origin_list == ["http://a.com", "http://b.com", "http://c.com"]


def test_webhook_url_list():
    """webhook_url_list should split comma-separated URLs."""
    from app.config import Settings

    s = Settings(
        DATABASE_URL="postgresql://x@localhost/x",
        WEBHOOK_URLS="http://hook1.com, http://hook2.com",
    )
    assert s.webhook_url_list == ["http://hook1.com", "http://hook2.com"]


def test_webhook_url_list_empty():
    """webhook_url_list should return empty list when WEBHOOK_URLS is empty."""
    from app.config import Settings

    s = Settings(
        DATABASE_URL="postgresql://x@localhost/x",
        WEBHOOK_URLS="",
    )
    assert s.webhook_url_list == []


def test_sendgrid_defaults():
    """SENDGRID_API_KEY should default to None."""
    from app.config import Settings

    s = Settings(DATABASE_URL="postgresql://x@localhost/x")
    assert s.SENDGRID_API_KEY is None
    assert s.SENDGRID_FROM_EMAIL == "noreply@incident-platform.local"
