# Database

PostgreSQL 16 instance (port 5432) serving as the shared persistent store for all platform services. Uses schema-level separation (alerts, incidents, oncall, notifications, analysis) to isolate service data. Initialized on first boot via a SQL script that creates schemas, ENUM types, tables, indexes, triggers, and seed data.

## Logic Flow

```text
PostgreSQL container starts
         │
  Run init-db/01-init-database.sql
         │
  Create extension: uuid-ossp
         │
  Create schemas: alerts, incidents, oncall, notifications, analysis
         │
  Create ENUM types: severity_level, alert_status,
  incident_status, user_role, notification_channel, notification_status
         │
  Create tables across all schemas
         │
  Create indexes for query performance
         │
  Create update_updated_at() trigger function
         │
  Attach triggers to alerts.alerts and incidents.incidents
         │
  Seed users: 9 engineers (admin + responder)
         │
  Seed oncall.schedules: 3 teams with rotation configs
         │
  Database ready for connections
```

## Purpose

PostgreSQL database providing schema-separated persistent storage for all platform services, initialized via a SQL script that creates schemas, tables, indexes, triggers, and seed data on first startup.

## Schemas

| Schema | Owner Service | Description |
| :--- | :--- | :--- |
| `public` | Shared | `users` table for engineer identities |
| `alerts` | Alert Ingestion | Raw alert storage and audit events |
| `incidents` | Incident Management | Incident records, alert linkage, notification log |
| `oncall` | On-Call Service | Schedules, assignments, escalation history |
| `notifications` | Notification Service | Notification delivery records |
| `analysis` | AI Analysis Service | Suggestions and resolved patterns |

## Tables

| Schema | Table | Primary Key | Description |
| :--- | :--- | :--- | :--- |
| `public` | `users` | `id` (UUID) | Engineer identities with name, email, phone, role |
| `alerts` | `alerts` | `id` (UUID) | Raw alert records with service, severity, labels |
| `alerts` | `alert_events` | `id` (UUID) | Alert audit log (created, acknowledged, escalated, resolved) |
| `incidents` | `incidents` | `id` (UUID) | Incident lifecycle records with MTTA/MTTR timestamps |
| `incidents` | `incident_alerts` | `(incident_id, alert_id)` | Many-to-many join between incidents and alerts |
| `incidents` | `notification_log` | `id` (UUID) | Historical notification dispatch records |
| `notifications` | `notifications` | `id` (UUID) | Notification delivery records per channel |
| `oncall` | `schedules` | `id` (UUID) | Rotation schedules with JSONB engineer lists |
| `oncall` | `oncall_assignments` | `id` (UUID) | Explicit on-call time-range assignments |
| `oncall` | `escalations` | `id` (UUID) | Escalation history with from/to engineer |
| `analysis` | `suggestions` | `suggestion_id` (SERIAL) | AI root-cause suggestions per alert/incident |
| `analysis` | `resolved_patterns` | `pattern_id` (SERIAL) | Learned patterns for future TF-IDF matching |

## ENUM Types

| Type | Values |
| :--- | :--- |
| `severity_level` | `critical`, `high`, `medium`, `low`, `info` |
| `alert_status` | `firing`, `acknowledged`, `resolved` |
| `incident_status` | `open`, `acknowledged`, `in_progress`, `investigating`, `mitigated`, `resolved`, `closed` |
| `user_role` | `admin`, `responder`, `viewer` |
| `alert_event_type` | `created`, `acknowledged`, `escalated`, `resolved`, `suppressed` |
| `notification_channel` | `email`, `sms`, `slack`, `pagerduty` |
| `notification_status` | `sent`, `delivered`, `failed` |

## Indexes

| Table | Index | Columns |
| :--- | :--- | :--- |
| `alerts.alerts` | `idx_alerts_service_severity` | `service`, `severity` |
| `alerts.alerts` | `idx_alerts_status` | `status` |
| `alerts.alerts` | `idx_alerts_fingerprint` | `fingerprint` |
| `alerts.alerts` | `idx_alerts_timestamp` | `timestamp` |
| `alerts.alerts` | `idx_alerts_incident_id` | `incident_id` |
| `alerts.alerts` | `idx_alerts_created_at` | `created_at` |
| `alerts.alert_events` | `idx_alert_events_alert` | `alert_id` |
| `incidents.incidents` | `idx_incidents_status` | `status` |
| `incidents.incidents` | `idx_incidents_service` | `service` |
| `incidents.incidents` | `idx_incidents_severity` | `severity` |
| `incidents.incidents` | `idx_incidents_created` | `created_at` |
| `incidents.notification_log` | `idx_notif_alert` | `alert_id` |
| `incidents.notification_log` | `idx_notif_incident` | `incident_id` |
| `notifications.notifications` | `idx_notifications_incident` | `incident_id` |
| `notifications.notifications` | `idx_notifications_channel` | `channel` |
| `notifications.notifications` | `idx_notifications_created` | `created_at` |
| `oncall.oncall_assignments` | `idx_oncall_team` | `team_name` |
| `oncall.oncall_assignments` | `idx_oncall_time` | `start_time`, `end_time` |
| `oncall.escalations` | `idx_escalations_incident` | `incident_id` |

## Triggers

| Trigger | Table | Function | Behavior |
| :--- | :--- | :--- | :--- |
| `trg_alerts_updated_at` | `alerts.alerts` | `update_updated_at()` | Sets `updated_at = now()` before each UPDATE |
| `trg_incidents_updated_at` | `incidents.incidents` | `update_updated_at()` | Sets `updated_at = now()` before each UPDATE |

## Configuration

| Variable | Description | Required |
| :--- | :--- | :--- |
| `POSTGRES_DB` | Database name | No (default: `incident_platform`) |
| `POSTGRES_USER` | Database superuser | No (default: `postgres`) |
| `POSTGRES_HOST_AUTH_METHOD` | Authentication method | No (default: `trust`) |

## Docker Volume

| Volume | Mount Point | Description |
| :--- | :--- | :--- |
| `db-data` | `/var/lib/postgresql/data` | Persistent database storage |

## Connection

```
postgresql://{POSTGRES_USER}@database:5432/{POSTGRES_DB}
```

All services connect via the `incident-platform` Docker bridge network using the hostname `database` on port `5432`.
