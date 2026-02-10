# Incident & On-Call Management Platform

> **OpenCode Hackathon 2026** — Production-ready incident management platform built with Python/FastAPI microservices, React frontend, PostgreSQL, and Prometheus + Grafana monitoring. Includes an NLP-powered AI analysis engine for root-cause suggestions.

---

## Quick Start (5 commands)

```bash
git clone <repo-url>        # 1. clone the repository
cd OpenCode14               # 2. navigate to project root
cp .env.example .env        # 3. configure environment
make setup                  # 4. create venv + install dependencies
make up                     # 5. start all services via Docker Compose
```

**That's it!** Open:

- **Web UI** → <http://localhost:8080>
- **Test Runner UI** → <http://localhost:8006>
- **Alert Ingestion API** → <http://localhost:8001/docs>
- **Incident Management API** → <http://localhost:8002/docs>
- **AI Analysis API** → <http://localhost:8005/docs>
- **Grafana Dashboards** → <http://localhost:3000> (admin/admin)
- **Prometheus** → <http://localhost:9090>

> **Full CI/CD pipeline** (lint → security → build → scan → test → deploy → verify):
>
> ```bash
> make all
> ```

### Send Test Data

Open the **Test Runner UI** at <http://localhost:8006> to:

- Browse 15 predefined alert scenarios grouped by category
- Send individual alerts or all at once with one click
- Create custom alerts with free-form fields
- Start continuous mode with configurable intervals
- Monitor service health and view live AI analysis results

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Web UI (:8080)                               │
│                     React + Nginx Proxy                             │
└────────┬──────────────────┬──────────────────┬──────────────────────┘
         │                  │                  │
         |                  |                  |
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Alert Ingestion│ │   Incident     │ │   On-Call &    │
│   :8001        │→│  Management    │→│  Escalation    │
│                │ │   :8002        │ │   :8003        │
└───────┬────────┘ └───────┬────────┘ └───────┬────────┘
        │                  │                  │
        │          ┌───────┴────────┐         │
        ├─────────→│  Notification  │←────────┘
        │          │   :8004        │
        │          └───────┬────────┘
        │                  │
┌───────┴────────┐         │
│  AI Analysis   │         │
│   :8005        │         │
│ (NLP / TF-IDF) │         │
└───────┬────────┘         │
        │                  │
┌──────────────────────────────────────┐
│         PostgreSQL (:5432)           │
│  schemas: alerts │ incidents │ oncall │ notifications │ analysis │
└──────────────────────────────────────┘
        │
┌───────┴──────────────────────────────┐
│     Prometheus (:9090) → Grafana     │
│          (:3000)                     │
└──────────────────────────────────────┘
```

### Data Flow: Alert → Resolution

1. External system sends `POST /api/v1/alerts` to Alert Ingestion (:8001)
2. Alert is validated, normalized, stored in `alerts.alerts`
3. Correlation engine checks for open incidents (same service + severity within 5-min window)
4. If match → attach to existing incident; if no match → create new incident via Incident Management
5. **AI Analysis Service** receives the alert asynchronously and returns root-cause suggestions via TF-IDF similarity
6. Incident Management assigns on-call engineer via On-Call Service
7. Notification Service alerts the engineer (email/webhook/mock)
8. Engineer acknowledges → MTTA calculated; resolves → MTTR calculated
9. All metrics exposed via Prometheus and visualized in Grafana dashboards

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Alert Ingestion** | 8001 | Receives, validates, stores, and correlates alerts |
| **Incident Management** | 8002 | CRUD for incidents, status transitions, MTTA/MTTR |
| **On-Call & Escalation** | 8003 | Rotation schedules, current on-call, auto-escalation |
| **Notification** | 8004 | Multi-channel notifications (mock, email, webhook) |
| **AI Analysis** | 8005 | NLP-powered root-cause analysis (TF-IDF + knowledge base) |
| **Web UI** | 8080 | React dashboard with live incident view + AI suggestions |
| **PostgreSQL** | 5432 | Persistent storage (5 schemas) |
| **Prometheus** | 9090 | Metrics collection (10s scrape) |
| **Grafana** | 3000 | 3 dashboards (incidents, SRE metrics, system health) |
| **Test Runner** | 8006 | Interactive web UI for sending test alerts + viewing AI analysis |

---

## API Documentation

Each service auto-generates interactive API docs via FastAPI:

| Service | Swagger UI |
|---------|-----------|
| Alert Ingestion | <http://localhost:8001/docs> |
| Incident Management | <http://localhost:8002/docs> |
| On-Call Service | <http://localhost:8003/docs> |
| Notification Service | <http://localhost:8004/docs> |
| AI Analysis | <http://localhost:8005/docs> |

### Key Endpoints

```bash
# Create an alert
curl -X POST http://localhost:8001/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '{"service":"payment-api","severity":"critical","message":"Error rate exceeded 5%"}'

# List incidents
curl http://localhost:8002/api/v1/incidents?status=open

# Get current on-call
curl http://localhost:8003/api/v1/oncall/current?team=platform

# Analyse an alert with AI
curl -X POST http://localhost:8005/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"message":"high cpu usage detected","service":"web-server","severity":"critical"}'

# Get AI suggestions for an incident
curl http://localhost:8005/api/v1/suggestions?incident_id=<uuid>

# Check health
curl http://localhost:8001/health
```

---

## CI/CD Pipeline (7 Stages)

```
make all → quality → security → build → scan → test → deploy → verify
```

| Stage | What | Tools |
|-------|------|-------|
| 1. Quality | Linting & formatting | flake8, pylint, black, isort |
| 2. Security | Credential scanning | gitleaks, trufflehog |
| 3. Build | Docker images | docker compose build |
| 4. Scan | Vulnerability scanning | Trivy |
| 5. Test | Unit + integration tests | pytest, coverage ≥60% |
| 6. Deploy | Start all services | docker compose up |
| 7. Verify | Health & smoke tests | curl, jq |

Run locally:

```bash
make all          # full pipeline
make lint         # just linting
make test         # just tests
make deploy       # build + start
make verify       # health + smoke tests
```

GitHub Actions CI runs automatically on push to `master` and on PRs.

---

## Monitoring & Observability

### Prometheus Metrics

All services expose `/metrics` in Prometheus format:

| Metric | Type | Description |
|--------|------|-------------|
| `alerts_received_total` | Counter | Total alerts by severity & service |
| `alerts_correlated_total` | Counter | Correlation results (new/existing incident) |
| `incidents_total` | Counter | Incidents by status & severity |
| `incident_mtta_seconds` | Histogram | Time to acknowledge |
| `incident_mttr_seconds` | Histogram | Time to resolve |
| `open_incidents` | Gauge | Current open incidents by severity |
| `http_requests_total` | Counter | HTTP requests by method/status/handler |
| `http_request_duration_seconds` | Histogram | Request latency |

### Grafana Dashboards

1. **Live Incident Overview** — Open incidents, MTTA/MTTR gauges, top noisy services
2. **SRE Performance Metrics** — MTTA/MTTR trends, incident volume, time distributions
3. **System Health** — Service availability, request/error rates, resource usage

---

## Project Structure

```
incident-platform/
├── alert-ingestion-service/    # FastAPI :8001
├── incident-management-service/# FastAPI :8002
├── oncall-service/             # FastAPI :8003
├── notification-service/       # FastAPI :8004
├── ai-analysis-service/        # FastAPI :8005 (NLP engine)
├── web-ui/                     # React :8080
├── test-runner/                # Test data generator (Docker)
├── database/                   # PostgreSQL init scripts
│   └── init-db/
│       └── 01-init-database.sql
├── monitoring/                 # Prometheus & Grafana config
│   └── grafana-dashboards/     # 5 auto-provisioned dashboards
├── docker-compose.yml          # All services orchestration
├── Makefile                    # 7-stage CI/CD pipeline
├── .env.example                # Environment template
├── .gitleaks.toml              # Credentials scanning config
└── .github/workflows/          # GitHub Actions CI (6 pipelines)
```

---

## Configuration

All services are configured via environment variables. See [`.env.example`](.env.example) for the full list.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:${POSTGRES_PASSWORD}@database:5432/incident_platform` | PostgreSQL connection |
| `CORRELATION_WINDOW_MINUTES` | `5` | Alert deduplication window |
| `INCIDENT_SERVICE_URL` | `http://incident-management:8002` | Incident service URL |
| `NOTIFICATION_SERVICE_URL` | `http://notification-service:8004` | Notification service URL |

---

## Security

- **Non-root containers** — All Dockerfiles run as unprivileged `appuser`
- **Multi-stage builds** — Minimal runtime images without build tools
- **No hardcoded secrets** — All credentials via environment variables
- **Credential scanning** — GitLeaks + TruffleHog in CI pipeline
- **Vulnerability scanning** — Trivy scans all container images
- **SARIF reports** — Scan results uploaded as CI artifacts

---

## License

MIT
