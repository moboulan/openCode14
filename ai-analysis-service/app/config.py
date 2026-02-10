"""Configuration for the AI analysis service."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://incident_user:incident_pass@database:5432/incident_platform"
    SERVICE_PORT: int = 8005

    # Peer service URLs (for fetching historical data)
    INCIDENT_SERVICE_URL: str = "http://incident-management:8002"

    # NLP tunables
    MIN_CONFIDENCE: float = 0.12
    TOP_K_SUGGESTIONS: int = 5
    HISTORICAL_REFRESH_INTERVAL: int = 300  # seconds

    class Config:
        env_prefix = ""
        extra = "ignore"


settings = Settings()
