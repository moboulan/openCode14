"""Tests for app/config.py — Settings."""

import os
from unittest.mock import patch


class TestSettings:
    def test_defaults(self):
        from app.config import Settings

        s = Settings()
        assert s.SERVICE_NAME == "incident-management"
        assert s.SERVICE_PORT == 8002
        assert s.ENVIRONMENT == "development"
        assert s.ESCALATION_TIMEOUT_MINUTES == 5
        assert s.LOG_LEVEL == "INFO"

    def test_env_override(self):
        from app.config import Settings

        with patch.dict(
            os.environ,
            {
                "SERVICE_NAME": "custom-name",
                "SERVICE_PORT": "9999",
                "DATABASE_URL": "postgresql://u:p@host/db",
                "ESCALATION_TIMEOUT_MINUTES": "15",
            },
        ):
            s = Settings()
            assert s.SERVICE_NAME == "custom-name"
            assert s.SERVICE_PORT == 9999
            assert s.DATABASE_URL == "postgresql://u:p@host/db"
            assert s.ESCALATION_TIMEOUT_MINUTES == 15
