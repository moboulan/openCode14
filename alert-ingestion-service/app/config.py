from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    SERVICE_NAME: str = "incident-platform-service"
    SERVICE_PORT: int = 8001
    ENVIRONMENT: str = "development"
    
    # Database configuration (change localhost to database)
    DATABASE_URL: str = "postgresql://postgres:hackathon2026@localhost:5432/incident_platform"
    
    # External service URLs
    INCIDENT_SERVICE_URL: Optional[str] = "http://incident-management:8002"
    ONCALL_SERVICE_URL: Optional[str] = "http://oncall-service:8003"
    ALERT_SERVICE_URL: Optional[str] = "http://alert-ingestion:8001"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
