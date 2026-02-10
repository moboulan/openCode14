# Test Runner

Standalone Python script (`test-runner.py` in the project root) that sends realistic test alerts to the running ExpertMind platform. Ships 15 predefined alert scenarios across 9 categories and supports on-call schedule setup, AI analysis, and continuous load generation.

**Zero dependencies** — uses only Python 3 stdlib (`urllib`, `json`, `argparse`).

## Usage

```bash
python3 test-runner.py                  # Health check + send all 15 scenarios
python3 test-runner.py --health         # Health check only
python3 test-runner.py --list           # List available scenarios
python3 test-runner.py --scenario cpu-high
python3 test-runner.py --setup-oncall   # Push 5 on-call schedules
python3 test-runner.py --continuous 10  # Send random alert every 10s (Ctrl+C to stop)
```

## Logic Flow

```text
  ╔═══════════════════════════════════════════════╗
  ║        python3 test-runner.py                 ║
  ╚═══════════════════════╤═══════════════════════╝
                          ▼
  ┌───────────────────────────────────────────────┐
  │              Parse flags                      │
  └──┬──────┬──────┬──────┬───────┬───────┬───────┘
     ▼      ▼      ▼      ▼       ▼       ▼
  ┌──────┐┌──────┐┌─────┐┌──────┐┌──────┐┌────────┐
  │health││ list ││scen.││ all  ││oncall││contin. │
  └──┬───┘└──┬───┘└──┬──┘└──┬───┘└──┬───┘└───┬────┘
     ▼       ▼       │      │       ▼        │
  ┌──────┐┌──────┐   │      │  ┌─────────┐   │
  │Probe ││Print │   │      │  │POST 5   │   │
  │5 svcs││table │   │      │  │schedules│   │
  └──────┘└──────┘   │      │  └─────────┘   │
                     ▼      ▼                ▼
            ┌─────────────────────────────────────┐
            │    POST alert to Alert Ingestion     │
            │            :8001                     │
            └─────────────────┬───────────────────┘
                              ▼
            ┌─────────────────────────────────────┐
            │    POST to AI Analysis :8005         │
            └─────────────────┬───────────────────┘
                              ▼
            ┌─────────────────────────────────────┐
            │    Print alert_id + incident_id      │
            │    + AI suggestions                  │
            └─────────────────────────────────────┘
```

## Configuration

| Env Variable      | Default                                         | Purpose              |
| ----------------- | ----------------------------------------------- | -------------------- |
| `ALERT_URL`       | `http://localhost:8001/api/v1/alerts`            | Alert ingestion      |
| `AI_ANALYSIS_URL` | `http://localhost:8005/api/v1/analyze`           | AI analysis          |
| `ONCALL_URL`      | `http://localhost:8003/api/v1`                   | On-call service      |

## Scenarios (15)

| ID             | Category   | Service              | Severity |
| -------------- | ---------- | -------------------- | -------- |
| cpu-high       | CPU        | payment-api          | critical |
| cpu-throttle   | CPU        | auth-service         | high     |
| mem-oom        | Memory     | user-service         | critical |
| mem-high       | Memory     | cache-service        | high     |
| disk-full      | Disk       | log-collector        | high     |
| net-timeout    | Network    | api-gateway          | critical |
| net-refused    | Network    | order-service        | high     |
| db-pool        | Database   | user-service         | critical |
| db-slow        | Database   | analytics-service    | medium   |
| http-500       | HTTP       | api-gateway          | critical |
| http-401       | HTTP       | auth-service         | medium   |
| ssl-expiry     | SSL/TLS    | api-gateway          | high     |
| k8s-crash      | Kubernetes | payment-api          | high     |
| k8s-hpa        | Kubernetes | notification-worker  | medium   |
| queue-backlog  | Queue      | order-processor      | high     |
