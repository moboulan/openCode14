from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service configuration
    SERVICE_NAME: str = "incident-management"
    SERVICE_PORT: int = 8002
    ENVIRONMENT: str = "development"
    APP_VERSION: str = "1.0.0"

    # Database configuration
    DATABASE_URL: str  # required — no insecure default

    # Database connection pool
    DB_POOL_MIN: int = 1
    DB_POOL_MAX: int = 10

    # Escalation
    ESCALATION_TIMEOUT_MINUTES: int = 5

    # HTTP client
    HTTP_CLIENT_TIMEOUT: float = 10.0

    # Health-check thresholds (percent)
    HEALTH_MEMORY_THRESHOLD: float = 90.0
    HEALTH_DISK_THRESHOLD: float = 90.0

    # CORS
    CORS_ORIGINS: str = "http://localhost:8080,http://localhost:3000"

    # External service URLs
    INCIDENT_SERVICE_URL: Optional[str] = "http://incident-management:8002"
    ONCALL_SERVICE_URL: Optional[str] = "http://oncall-service:8003"
    ALERT_SERVICE_URL: Optional[str] = "http://alert-ingestion:8001"
    NOTIFICATION_SERVICE_URL: Optional[str] = "http://notification-service:8004"

    # Prometheus histogram buckets (comma-separated)
    MTTA_BUCKETS: str = "30,60,120,300,600,1800,3600"
    MTTR_BUCKETS: str = "300,600,1800,3600,7200,14400,28800"

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def mtta_bucket_list(self) -> list[float]:
        return [float(b) for b in self.MTTA_BUCKETS.split(",")]

    @property
    def mttr_bucket_list(self) -> list[float]:
        return [float(b) for b in self.MTTR_BUCKETS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
