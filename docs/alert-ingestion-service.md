# Alert Ingestion Service

FastAPI microservice (port 8001) that receives incoming alerts via REST, validates and normalizes their schema, stores them in PostgreSQL, and correlates them against open incidents within a configurable time window. When no matching incident exists, it creates one by calling the Incident Management Service.

## Logic Flow

```text
POST /api/v1/alerts
         │
  Validate schema (Pydantic)
         │
  Normalize severity to enum
         │
  Generate unique alert_id
         │
  Store raw alert in alerts.alerts
         │
  Correlation query: same service + severity
  within CORRELATION_WINDOW_MINUTES, status IN (open, acknowledged)
         │
    Match found?
      ├── Yes → Link alert to existing incident (incident_alerts)
      │         Update alert row with incident FK
      │
      └── No  → POST to Incident Management /api/v1/incidents
                    │
               Incident created?
                 ├── Yes → Link alert to new incident
                 └── No  → Graceful degradation (incident_id = null)
         │
  Increment Prometheus counters
         │
  Return AlertResponse
```

## Purpose

Receives, validates, stores, and correlates incoming alerts against open incidents, creating new incidents via the Incident Management Service when no correlation match is found within the configured time window.

## Configuration

| Variable | Description | Required |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SERVICE_NAME` | Service identifier | No (default: `alert-ingestion`) |
| `SERVICE_PORT` | HTTP listen port | No (default: `8001`) |
| `ENVIRONMENT` | Runtime environment label | No (default: `development`) |
| `APP_VERSION` | Reported application version | No (default: `1.0.0`) |
| `DB_POOL_MIN` | Minimum database connections in pool | No (default: `1`) |
| `DB_POOL_MAX` | Maximum database connections in pool | No (default: `10`) |
| `CORRELATION_WINDOW_MINUTES` | Time window for alert-to-incident correlation | No (default: `5`) |
| `HTTP_CLIENT_TIMEOUT` | Timeout in seconds for outbound HTTP calls | No (default: `10.0`) |
| `HEALTH_MEMORY_THRESHOLD` | Memory usage percentage triggering degraded health | No (default: `90.0`) |
| `HEALTH_DISK_THRESHOLD` | Disk usage percentage triggering degraded health | No (default: `90.0`) |
| `CORS_ORIGINS` | Comma-separated allowed CORS origins | No (default: `http://localhost:8080,http://localhost:3000`) |
| `INCIDENT_SERVICE_URL` | Base URL of the Incident Management Service | No (default: `http://incident-management:8002`) |
| `NOTIFICATION_SERVICE_URL` | Base URL of the Notification Service | No (default: `http://notification-service:8004`) |
| `LOG_LEVEL` | Python logging level | No (default: `INFO`) |

## Endpoints

| Method | Path | Description | Status Codes |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/alerts` | Receive, store, and correlate an alert | `201`, `422` |
| `GET` | `/api/v1/alerts/{alert_id}` | Retrieve a single alert by ID | `200`, `404` |
| `GET` | `/api/v1/alerts` | List alerts with optional `service`, `severity`, `limit`, `offset` filters | `200` |
| `GET` | `/health` | Full health check (database, memory, disk) | `200`, `503` |
| `GET` | `/health/ready` | Readiness probe (database connectivity) | `200`, `503` |
| `GET` | `/health/live` | Liveness probe | `200` |
| `GET` | `/metrics` | Prometheus metrics endpoint | `200` |

## Prometheus Metrics

| Metric | Type | Labels | Description |
| :--- | :--- | :--- | :--- |
| `alerts_received_total` | Counter | `severity`, `service` | Total number of alerts received |
| `alerts_correlated_total` | Counter | `result` | Alerts correlated to incidents (values: `new_incident`, `existing_incident`) |

## Data Model

```
alerts.alerts
├── id             UUID (PK)
├── alert_id       VARCHAR(255) UNIQUE
├── service        VARCHAR(255)
├── severity       severity_level ENUM
├── message        TEXT
├── labels         JSONB
├── timestamp      TIMESTAMPTZ
├── incident_id    UUID (FK -> incidents.incidents)
└── created_at     TIMESTAMPTZ
```

## Inter-Service Communication

| Target Service | Method | Endpoint | Trigger |
| :--- | :--- | :--- | :--- |
| Incident Management | `POST` | `/api/v1/incidents` | No correlation match found for incoming alert |
