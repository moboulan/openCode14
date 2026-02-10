import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import close_pool
from app.metrics import setup_custom_metrics
from app.routers import api, health
from app.routers.api import check_escalations

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} on port {settings.SERVICE_PORT}")
    logger.info(f"Metrics available at http://localhost:{settings.SERVICE_PORT}/metrics")
    logger.info(f"Health check at http://localhost:{settings.SERVICE_PORT}/health")
    # Start background escalation task
    task = asyncio.create_task(_escalation_loop())
    yield
    # Shutdown
    task.cancel()
    close_pool()
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


async def _escalation_loop():
    """Background loop that runs auto-escalation every 60 seconds."""
    while True:
        await asyncio.sleep(60)
        try:
            await check_escalations()
            logger.info("Auto-escalation task executed successfully.")
        except Exception as e:
            logger.error(f"Auto-escalation task failed: {e}")


# Create FastAPI app
app = FastAPI(
    title="On-Call & Escalation Service",
    description="On-call scheduling and escalation microservice for Incident & On-Call Management Platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS -- restrict to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup Prometheus metrics
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health", "/health/ready", "/health/live"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)

instrumentator.instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")

# Setup custom metrics
setup_custom_metrics()


# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception handler caught: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": type(exc).__name__,
                "timestamp": time.time(),
            }
        },
    )


# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(api.router, prefix="/api/v1", tags=["api"])


# Root endpoint
@app.get("/")
async def root():
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
    }
