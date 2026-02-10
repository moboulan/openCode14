import time
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter, Response, status

from app.config import settings
from app.database import check_database_health
from app.models import HealthCheck

router = APIRouter()

# Track service start time
service_start_time = time.time()


@router.get("/health", response_model=HealthCheck)
def health_check(response: Response):
    """
    Health check endpoint with dependency checks
    Returns 200 if healthy, 503 if degraded
    """
    health_status = "healthy"
    checks = {"database": "unknown", "memory": "healthy", "disk": "healthy"}

    # Check database
    if check_database_health():
        checks["database"] = "healthy"
    else:
        checks["database"] = "unhealthy"
        health_status = "degraded"

    # Check memory usage
    memory_percent = psutil.virtual_memory().percent
    if memory_percent > settings.HEALTH_MEMORY_THRESHOLD:
        checks["memory"] = "warning"
        health_status = "degraded"

    # Check disk usage
    disk_percent = psutil.disk_usage("/").percent
    if disk_percent > settings.HEALTH_DISK_THRESHOLD:
        checks["disk"] = "warning"
        health_status = "degraded"

    uptime = time.time() - service_start_time

    response.status_code = status.HTTP_200_OK if health_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheck(
        status=health_status,
        timestamp=datetime.now(timezone.utc),
        service=settings.SERVICE_NAME,
        version=settings.APP_VERSION,
        uptime=uptime,
        checks=checks,
    )


@router.get("/health/ready")
def readiness_check(response: Response):
    """Readiness probe - can service accept traffic?"""
    if check_database_health():
        return {"status": "ready"}
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready"}


@router.get("/health/live")
async def liveness_check():
    """Liveness probe - is service running?"""
    return {"status": "alive"}
