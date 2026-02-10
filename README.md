# Incident & On-Call Management Platform

> **OpenCode Hackathon 2026** — Production-ready incident management platform built with Python/FastAPI microservices, React frontend, PostgreSQL, and Prometheus + Grafana monitoring.

---

## Quick Start (≤5 commands)

```bash
git clone <repo-url> && cd incident-platform
cp .env.example .env          # configure environment
make build                    # build all Docker images
make up                       # start all services
make health                   # verify everything is healthy
```

**That's it!** Open:

- **Web UI** → <http://localhost:8080>
- **Alert Ingestion API** → <http://localhost:8001/docs>
- **Incident Management API** → <http://localhost:8002/docs>
- **Grafana Dashboards** → <http://localhost:3000> (admin/admin)
- **Prometheus** → <http://localhost:9090>

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
        │          │  Notification  │←────────┘
        │          │   :8004        │
        │          └───────┬────────┘
        │                  │
        |                  |
┌──────────────────────────────────────┐
│         PostgreSQL (:5432)           │
│  schemas: alerts │ incidents │ oncall │ notifications │
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
5. Incident Management assigns on-call engineer via On-Call Service
6. Notification Service alerts the engineer (email/webhook/mock)
7. Engineer acknowledges → MTTA calculated; resolves → MTTR calculated
8. All metrics exposed via Prometheus and visualized in Grafana dashboards

---

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Alert Ingestion** | 8001 | Receives, validates, stores, and correlates alerts |
| **Incident Management** | 8002 | CRUD for incidents, status transitions, MTTA/MTTR |
| **On-Call & Escalation** | 8003 | Rotation schedules, current on-call, auto-escalation |
| **Notification** | 8004 | Multi-channel notifications (mock, email, webhook) |
| **Web UI** | 8080 | React dashboard with live incident view |
| **PostgreSQL** | 5432 | Persistent storage (4 schemas) |
| **Prometheus** | 9090 | Metrics collection (10s scrape) |
| **Grafana** | 3000 | 3 dashboards (incidents, SRE metrics, system health) |

---

## API Documentation

Each service auto-generates interactive API docs via FastAPI:

| Service | Swagger UI |
|---------|-----------|
| Alert Ingestion | <http://localhost:8001/docs> |
| Incident Management | <http://localhost:8002/docs> |
| On-Call Service | <http://localhost:8003/docs> |
| Notification Service | <http://localhost:8004/docs> |

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
├── web-ui/                     # React :8080
├── database/                   # PostgreSQL init scripts
│   └── init-db/
│       └── 01-init-database.sql
├── monitoring/                 # Prometheus & Grafana config
├── docker-compose.yml          # All services orchestration
├── Makefile                    # 7-stage CI/CD pipeline
├── .env.example                # Environment template
├── .gitleaks.toml              # Credentials scanning config
└── .github/workflows/          # GitHub Actions CI
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
