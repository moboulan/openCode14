from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    SERVICE_NAME: str = "incident-management"
    SERVICE_PORT: int = 8002
    ENVIRONMENT: str = "development"

    # Database configuration
    DATABASE_URL: str = "postgresql://postgres:hackathon2026@localhost:5432/incident_platform"

    # Escalation
    ESCALATION_TIMEOUT_MINUTES: int = 5

    # External service URLs
    INCIDENT_SERVICE_URL: Optional[str] = "http://incident-management:8002"
    ONCALL_SERVICE_URL: Optional[str] = "http://oncall-service:8003"
    ALERT_SERVICE_URL: Optional[str] = "http://alert-ingestion:8001"
    NOTIFICATION_SERVICE_URL: Optional[str] = "http://notification-service:8004"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
