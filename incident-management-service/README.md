# Python FastAPI Microservice Template

FastAPI microservice with Prometheus metrics and health checks for the Incident Platform.

## Features

- ✅ FastAPI web framework
- ✅ Prometheus metrics with custom incident metrics
- ✅ Health check endpoints (/health, /ready, /live)
- ✅ Pydantic models for request/response validation
- ✅ Multi-stage Docker build
- ✅ Non-root user execution
- ✅ PostgreSQL integration ready
- ✅ Structured logging

## Quick Start

### Local Development

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
Install dependencies:

bash
pip install -r requirements.txt
Set environment variables:

bash
cp .env.example .env
Run development server:

bash
uvicorn app.main:app --reload --port 8001
Run tests:

bash
pytest --cov=app
Docker
Build image:

bash
docker build -t alert-ingestion:latest .
Run container:

bash
docker run -p 8001:8001 \
  -e DATABASE_URL=postgresql://postgres:hackathon2026@database:5432/incident_platform \
  alert-ingestion:latest
API Endpoints
Endpoint	Method	Description
/	GET	Service info
/health	GET	Health check with dependencies
/health/ready	GET	Readiness probe
/health/live	GET	Liveness probe
/metrics	GET	Prometheus metrics
/api/v1/alerts	POST	Create alert
/api/v1/alerts/:id	GET	Get alert by ID
/api/v1/alerts	GET	List alerts
/docs	GET	Interactive API documentation (Swagger)
/redoc	GET	Alternative API documentation
Metrics Exposed
alerts_received_total{severity, service} - Counter of alerts received

alerts_correlated_total{result} - Counter of alerts correlated

incidents_total{status, severity} - Counter of incidents

incident_mtta_seconds - Histogram of time to acknowledge

incident_mttr_seconds - Histogram of time to resolve

open_incidents{severity} - Gauge of open incidents

http_requests_inprogress - In-flight HTTP requests

http_request_duration_seconds - HTTP request latency

Environment Variables
Variable	Default	Description
SERVICE_NAME	incident-platform-service	Service name
SERVICE_PORT	8001	Port to run on
DATABASE_URL	(see .env.example)	PostgreSQL connection
INCIDENT_SERVICE_URL	http://incident-management:8002	Incident service URL
ONCALL_SERVICE_URL	http://oncall-service:8003	On-call service URL
ENVIRONMENT	development	Environment name
LOG_LEVEL	INFO	Logging level
Project Structure
text
app/
├── main.py           # FastAPI app and middleware
├── config.py         # Configuration management
├── metrics.py        # Custom Prometheus metrics
├── models.py         # Pydantic models
├── database.py       # Database utilities
└── routers/
    ├── health.py     # Health check endpoints
    └── api.py        # API endpoints
Testing Alert Creation
bash
curl -X POST http://localhost:8001/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "service": "frontend-api",
    "severity": "high",
    "message": "High CPU usage detected",
    "labels": {"environment": "production", "region": "us-east-1"}
  }'
Next Steps
Implement business logic in app/routers/api.py

Add database models and queries

Add unit tests with pytest

Configure CI/CD pipeline

Add OpenAPI schema customization

text

---

## Usage

This FastAPI template provides:
- Modern Python async framework
- Built-in API documentation (Swagger/ReDoc)
- Type safety with Pydantic
- Production-ready structure
- Prometheus metrics integration

**Saves 2-3 hours** of boilerplate setup!