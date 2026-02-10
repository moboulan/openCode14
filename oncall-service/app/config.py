from typing import List, Optional

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    SERVICE_NAME: str = "oncall-service"
    SERVICE_PORT: int = 8003
    ENVIRONMENT: str = "development"
    APP_VERSION: str = "1.0.0"

    # Database configuration
    DATABASE_URL: str  # required -- no insecure default

    # Database connection pool
    DB_POOL_MIN: int = 1
    DB_POOL_MAX: int = 10

    # HTTP client
    HTTP_CLIENT_TIMEOUT: float = 10.0

    # Health-check thresholds (percent)
    HEALTH_MEMORY_THRESHOLD: float = 90.0
    HEALTH_DISK_THRESHOLD: float = 90.0

    # CORS
    CORS_ORIGINS: str = "http://localhost:8080,http://localhost:3000"

    # External service URLs
    INCIDENT_SERVICE_URL: Optional[str] = "http://incident-management:8002"
    NOTIFICATION_SERVICE_URL: Optional[str] = "http://notification-service:8004"
    ALERT_SERVICE_URL: Optional[str] = "http://alert-ingestion:8001"

    # Escalation defaults
    DEFAULT_ESCALATION_MINUTES: int = 5
    MANAGER_EMAIL: str = "admin@expertmind.local"
    ESCALATION_LOOP_COUNT: int = 2

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = ConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
