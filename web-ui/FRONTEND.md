# Frontend API Reference

All requests go through the **nginx reverse proxy** on port `8080`. The proxy maps URL prefixes to backend services:

| Nginx Path Prefix | Backend Target |
|---|---|
| `/api/alert-ingestion/` | `http://alert-ingestion:8001/` |
| `/api/incident-management/` | `http://incident-management:8002/` |
| `/api/oncall-service/` | `http://oncall-service:8003/` |
| `/api/notification-service/` | `http://notification-service:8004/` |
| `/ws/` | `http://incident-management:8002/ws/` (WebSocket upgrade) |

---

## Table of Contents

- [Alert Ingestion](#1-alert-ingestion-service)
- [Incident Management](#2-incident-management-service)
- [On-Call & Escalation](#3-on-call--escalation-service)
- [Notification](#4-notification-service)
- [WebSocket](#5-websocket-real-time-events)
- [Frontend Pages → API Mapping](#6-frontend-pages--api-mapping)
- [Quick Reference Table](#7-quick-reference)

---

## 1. Alert Ingestion Service

Base URL (through nginx): `/api/alert-ingestion/api/v1`

### `POST /api/v1/alerts` — Create Alert

Receives an alert, stores it, correlates with existing incidents. If a matching open/acknowledged incident exists (same service + severity within correlation window), the alert is linked to it. Otherwise a new incident is created via the Incident Management service.

**Request Body:**

```json
{
  "service": "payment-api",          // required — service name
  "severity": "critical",            // required — "critical" | "high" | "medium" | "low"
  "message": "High error rate",      // required — alert message
  "labels": { "env": "prod" },       // optional — key-value labels (default: {})
  "timestamp": "2026-02-09T10:00:00" // optional — ISO 8601 (default: now)
}
```

**Response (201):**

```json
{
  "alert_id": "alert-a1b2c3d4e5f6",
  "incident_id": "inc-f6e5d4c3b2a1",  // or null
  "status": "processed",
  "action": "new_incident",             // or "existing_incident"
  "timestamp": "2026-02-09T10:00:01Z"
}
```

---

### `GET /api/v1/alerts` — List Alerts

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `service` | string | — | Filter by service name |
| `severity` | string | — | `"critical"` \| `"high"` \| `"medium"` \| `"low"` |
| `limit` | int | `100` | Max results (1–1000) |

**Response (200):**

```json
{
  "alerts": [
    {
      "alert_id": "alert-a1b2c3d4e5f6",
      "service": "payment-api",
      "severity": "critical",
      "message": "High error rate",
      "labels": { "env": "prod" },
      "timestamp": "2026-02-09T10:00:00Z",
      "incident_id": "inc-f6e5d4c3b2a1",
      "created_at": "2026-02-09T10:00:01Z"
    }
  ],
  "total": 1
}
```

---

### `GET /api/v1/alerts/{alert_id}` — Get Single Alert

**Path Parameters:** `alert_id` (string)

**Response (200):** Single alert object (same shape as list items above).

**Error (404):** `{ "detail": "Alert not found" }`

---

## 2. Incident Management Service

Base URL (through nginx): `/api/incident-management/api/v1`

### `POST /api/v1/incidents` — Create Incident

Creates a new incident. Auto-assigns from on-call schedule if `assigned_to` is omitted. Sends a notification to the assigned engineer. Broadcasts `incident_created` via WebSocket.

**Request Body:**

```json
{
  "title": "Payment API High Error Rate",  // required — max 500 chars
  "service": "payment-api",                 // required
  "severity": "critical",                   // required — "critical" | "high" | "medium" | "low"
  "assigned_to": "alice@company.com"        // optional — auto-assigned from on-call if omitted
}
```

**Response (201):**

```json
{
  "incident_id": "inc-f6e5d4c3b2a1",
  "title": "Payment API High Error Rate",
  "service": "payment-api",
  "severity": "critical",
  "status": "open",
  "assigned_to": "alice@company.com",
  "created_at": "2026-02-09T10:00:01Z",
  "acknowledged_at": null,
  "resolved_at": null,
  "mtta_seconds": null,
  "mttr_seconds": null,
  "notes": []
}
```

---

### `GET /api/v1/incidents` — List Incidents

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `status` | string | — | `"open"` \| `"acknowledged"` \| `"resolved"` |
| `severity` | string | — | `"critical"` \| `"high"` \| `"medium"` \| `"low"` |
| `service` | string | — | Filter by service name |
| `limit` | int | `100` | Max results (1–1000) |

**Response (200):**

```json
{
  "incidents": [
    {
      "incident_id": "inc-f6e5d4c3b2a1",
      "title": "Payment API High Error Rate",
      "service": "payment-api",
      "severity": "critical",
      "status": "open",
      "assigned_to": "alice@company.com",
      "created_at": "2026-02-09T10:00:01Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "mtta_seconds": null,
      "mttr_seconds": null,
      "notes": []
    }
  ],
  "total": 1
}
```

---

### `GET /api/v1/incidents/{incident_id}` — Get Incident Detail

Returns the incident with its timeline and linked alerts.

**Path Parameters:** `incident_id` (string)

**Response (200):**

```json
{
  "incident_id": "inc-f6e5d4c3b2a1",
  "title": "Payment API High Error Rate",
  "service": "payment-api",
  "severity": "critical",
  "status": "acknowledged",
  "assigned_to": "alice@company.com",
  "created_at": "2026-02-09T10:00:01Z",
  "acknowledged_at": "2026-02-09T10:02:30Z",
  "resolved_at": null,
  "mtta_seconds": 149.0,
  "mttr_seconds": null,
  "notes": ["Investigating root cause"],
  "alerts": [
    {
      "alert_id": "alert-a1b2c3d4e5f6",
      "service": "payment-api",
      "severity": "critical",
      "message": "High error rate",
      "timestamp": "2026-02-09T10:00:00Z"
    }
  ],
  "timeline": [
    { "event": "created", "timestamp": "2026-02-09T10:00:01Z" },
    { "event": "acknowledged", "timestamp": "2026-02-09T10:02:30Z" }
  ]
}
```

**Error (404):** `{ "detail": "Incident not found" }`

---

### `PATCH /api/v1/incidents/{incident_id}` — Update Incident

Update status (acknowledge/resolve), reassign, or add notes. Broadcasts WebSocket events. Calculates MTTA on acknowledge and MTTR on resolve.

**Path Parameters:** `incident_id` (string)

**Request Body** (all fields optional, at least one required):

```json
{
  "status": "acknowledged",              // "open" | "acknowledged" | "resolved"
  "assigned_to": "bob@company.com",      // reassign
  "notes": ["Root cause identified"]     // notes to append (not replace)
}
```

**Response (200):** Updated incident object (same shape as create response).

**Errors:**

- **400:** `{ "detail": "No fields to update" }`
- **404:** `{ "detail": "Incident not found" }`

**Side Effects:**

- `status → "acknowledged"` → sets `acknowledged_at = now`, calculates `mtta_seconds`, broadcasts `incident_acknowledged`
- `status → "resolved"` → sets `resolved_at = now`, calculates `mttr_seconds`, broadcasts `incident_resolved`
- Any other update → broadcasts `incident_updated`

---

### `GET /api/v1/incidents/analytics` — Incident Analytics

Aggregated MTTA/MTTR statistics and per-service breakdown.

**Response (200):**

```json
{
  "summary": {
    "total": 42,
    "open_count": 5,
    "ack_count": 12,
    "resolved_count": 25,
    "avg_mtta": 120.5,
    "avg_mttr": 3600.0,
    "min_mtta": 10.0,
    "max_mtta": 600.0,
    "min_mttr": 300.0,
    "max_mttr": 14400.0
  },
  "by_service": [
    {
      "service": "payment-api",
      "count": 15,
      "avg_mtta": 90.2,
      "avg_mttr": 2800.0
    }
  ]
}
```

---

### `GET /api/v1/incidents/{incident_id}/metrics` — Incident Metrics

MTTA/MTTR for a specific incident.

**Path Parameters:** `incident_id` (string)

**Response (200):**

```json
{
  "incident_id": "inc-f6e5d4c3b2a1",
  "mtta_seconds": 149.0,
  "mttr_seconds": 3600.0,
  "created_at": "2026-02-09T10:00:01Z",
  "acknowledged_at": "2026-02-09T10:02:30Z",
  "resolved_at": "2026-02-09T11:00:01Z"
}
```

---

## 3. On-Call & Escalation Service

Base URL (through nginx): `/api/oncall-service/api/v1`

### `GET /api/v1/schedules` — List Schedules

**Response (200):**

```json
{
  "schedules": [
    {
      "id": 1,
      "team": "platform",
      "rotation_type": "daily",
      "start_date": "2026-02-01",
      "engineers": ["alice@company.com", "bob@company.com"],
      "escalation_minutes": 5,
      "created_at": "2026-02-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

---

### `POST /api/v1/schedules` — Create Schedule

**Request Body:**

```json
{
  "team": "platform",               // required
  "rotation_type": "daily",         // required — "daily" | "weekly"
  "start_date": "2026-02-01",       // required — YYYY-MM-DD
  "engineers": ["alice", "bob"],    // required — list of names/emails
  "escalation_minutes": 5           // optional — default: 5, min: 1
}
```

**Response (201):** Schedule object (same shape as list items above).

---

### `GET /api/v1/oncall/current` — Current On-Call

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `team` | string | No | Filter by team name |

**Response with `?team=platform` (200):**

```json
{
  "team": "platform",
  "primary": "alice@company.com",
  "secondary": "bob@company.com",
  "escalation_minutes": 5
}
```

**Response without `team` param (200):**

```json
{
  "oncall": [
    { "team": "platform", "primary": "alice@company.com", "secondary": "bob@company.com" },
    { "team": "backend", "primary": "charlie@company.com", "secondary": "diana@company.com" }
  ]
}
```

If a team has no schedule: `{ "team": "unknown", "primary": "unassigned", "secondary": null }`

---

### `POST /api/v1/escalate` — Escalate Incident

Escalates an incident to the secondary on-call engineer. Fetches the incident, finds secondary, records escalation, reassigns, and sends notification.

**Request Body:**

```json
{
  "incident_id": "inc-f6e5d4c3b2a1",    // required
  "reason": "No response after 5 min"    // optional — default: "Escalation timeout"
}
```

**Response (200):**

```json
{
  "incident_id": "inc-f6e5d4c3b2a1",
  "escalated_from": "alice@company.com",
  "escalated_to": "bob@company.com",
  "reason": "No response after 5 min",
  "timestamp": "2026-02-09T10:05:01Z"
}
```

**Errors:**

- **404:** Incident not found or no schedule for team
- **502:** Failed to communicate with incident management service

---

## 4. Notification Service

Base URL (through nginx): `/api/notification-service/api/v1`

### `POST /api/v1/notify` — Send Notification

> **Note:** This endpoint is called **service-to-service** (by incident-management and oncall-service). No frontend page currently invokes it directly.

**Request Body:**

```json
{
  "incident_id": "inc-f6e5d4c3b2a1",   // optional
  "engineer": "alice@company.com",       // required
  "channel": "mock",                     // optional — "mock" | "email" | "webhook" (default: "mock")
  "message": "New incident assigned"     // required
}
```

**Response (201):**

```json
{
  "notification_id": "notif-a1b2c3d4e5f6",
  "incident_id": "inc-f6e5d4c3b2a1",
  "engineer": "alice@company.com",
  "channel": "mock",
  "status": "sent",
  "timestamp": "2026-02-09T10:00:02Z"
}
```

---

### `GET /api/v1/notifications` — List Notifications

**Query Parameters:**

| Param | Type | Default | Description |
|---|---|---|---|
| `incident_id` | string | — | Filter by incident |
| `engineer` | string | — | Filter by engineer |
| `limit` | int | `100` | Max results (1–1000) |

**Response (200):**

```json
{
  "notifications": [
    {
      "notification_id": "notif-a1b2c3d4e5f6",
      "incident_id": "inc-f6e5d4c3b2a1",
      "engineer": "alice@company.com",
      "channel": "mock",
      "message": "New incident assigned",
      "status": "sent",
      "created_at": "2026-02-09T10:00:02Z"
    }
  ],
  "total": 1
}
```

---

## 5. WebSocket — Real-Time Events

### `WS /ws/events`

Connect through nginx at `ws://<host>/ws/events` (or `wss://` over TLS).

**Client → Server:**

- Send `"ping"` text frame → receives `{"event": "pong"}`

**Server → Client** (broadcast on incident changes):

```json
{
  "event": "incident_created",
  "data": { /* full incident object */ },
  "timestamp": "2026-02-09T10:00:01Z"
}
```

**Event Types:**

| Event | Trigger |
|---|---|
| `incident_created` | `POST /api/v1/incidents` |
| `incident_acknowledged` | `PATCH` with `status: "acknowledged"` |
| `incident_resolved` | `PATCH` with `status: "resolved"` |
| `incident_updated` | `PATCH` with other field changes |
| `pong` | Client sent `"ping"` |

**Frontend Usage** (React hook):

```javascript
import { useIncidentSocket } from '../hooks/useIncidentSocket';

const { connected } = useIncidentSocket((event) => {
  // event = { event: "incident_created", data: {...}, timestamp: "..." }
  console.log(event.event, event.data);
});
```

The hook auto-reconnects every 3 seconds and sends ping every 30 seconds as a keepalive.

---

## 6. Frontend Pages → API Mapping

### Dashboard (`/`)

| When | API Call | Purpose |
|---|---|---|
| On mount + every 30s | `GET /api/incident-management/api/v1/incidents?limit=50` | Load incident list |
| On mount + every 30s | `GET /api/incident-management/api/v1/incidents/analytics` | Load MTTA/MTTR stats |
| On WebSocket event | `GET /api/incident-management/api/v1/incidents/analytics` | Refresh analytics |
| Real-time | `WS /ws/events` | Live incident updates |

### Incident Detail (`/incidents/:id`)

| When | API Call | Purpose |
|---|---|---|
| On mount | `GET /api/incident-management/api/v1/incidents/{id}` | Load incident + timeline + alerts |
| Acknowledge button | `PATCH /api/incident-management/api/v1/incidents/{id}` | `{ "status": "acknowledged" }` |
| Resolve button | `PATCH /api/incident-management/api/v1/incidents/{id}` | `{ "status": "resolved" }` |

### On-Call Schedule (`/oncall`)

| When | API Call | Purpose |
|---|---|---|
| On mount | `GET /api/oncall-service/api/v1/schedules` | Load all schedules |
| On mount | `GET /api/oncall-service/api/v1/oncall/current` | Load current on-call for all teams |

### SRE Metrics (`/metrics`)

| When | API Call | Purpose |
|---|---|---|
| On mount + every 15s | `GET /api/incident-management/api/v1/incidents/analytics` | Load MTTA/MTTR aggregations |

---

## 7. Quick Reference

| # | Method | Frontend URL (via nginx) | Used By |
|---|---|---|---|
| 1 | `POST` | `/api/alert-ingestion/api/v1/alerts` | API client (available) |
| 2 | `GET` | `/api/alert-ingestion/api/v1/alerts` | API client (available) |
| 3 | `GET` | `/api/alert-ingestion/api/v1/alerts/{id}` | API client (available) |
| 4 | `POST` | `/api/incident-management/api/v1/incidents` | API client (available) |
| 5 | `GET` | `/api/incident-management/api/v1/incidents` | Dashboard |
| 6 | `GET` | `/api/incident-management/api/v1/incidents/analytics` | Dashboard, SRE Metrics |
| 7 | `GET` | `/api/incident-management/api/v1/incidents/{id}` | Incident Detail |
| 8 | `GET` | `/api/incident-management/api/v1/incidents/{id}/metrics` | API client (available) |
| 9 | `PATCH` | `/api/incident-management/api/v1/incidents/{id}` | Incident Detail |
| 10 | `WS` | `/ws/events` | Dashboard (real-time) |
| 11 | `GET` | `/api/oncall-service/api/v1/schedules` | On-Call Schedule |
| 12 | `GET` | `/api/oncall-service/api/v1/oncall/current` | On-Call Schedule |
| 13 | `POST` | `/api/oncall-service/api/v1/escalate` | API client (available) |
| 14 | `GET` | `/api/notification-service/api/v1/notifications` | API client (available) |

> **"API client (available)"** = defined in `services/web-ui/src/services/api.js` but not currently called from any page component. Ready for future use.

---

## Enums

**SeverityLevel:** `"critical"` | `"high"` | `"medium"` | `"low"`

**IncidentStatus:** `"open"` | `"acknowledged"` | `"resolved"`

**RotationType:** `"daily"` | `"weekly"`

**NotificationChannel:** `"mock"` | `"email"` | `"webhook"`
