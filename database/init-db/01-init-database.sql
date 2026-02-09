-- ============================================================
-- Incident Platform — PostgreSQL schema
-- ============================================================

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas for each service
CREATE SCHEMA IF NOT EXISTS alerts;
CREATE SCHEMA IF NOT EXISTS incidents;
CREATE SCHEMA IF NOT EXISTS oncall;

-- ── ENUM types ──────────────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE severity_level AS ENUM ('critical', 'high', 'medium', 'low', 'info');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE alert_status AS ENUM ('firing', 'acknowledged', 'resolved');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE incident_status AS ENUM (
        'open', 'acknowledged', 'in_progress',
        'investigating', 'mitigated', 'resolved', 'closed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'responder', 'viewer');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE alert_event_type AS ENUM (
        'created', 'acknowledged', 'escalated', 'resolved', 'suppressed'
    );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notification_channel AS ENUM ('email', 'sms', 'slack', 'pagerduty');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
    CREATE TYPE notification_status AS ENUM ('sent', 'delivered', 'failed');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Users (public schema) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT        NOT NULL,
    email       TEXT        NOT NULL UNIQUE,
    phone       TEXT,
    role        user_role   NOT NULL DEFAULT 'responder',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Alerts schema tables ────────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts.alerts (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id      VARCHAR(255) UNIQUE NOT NULL,
    external_id   TEXT,
    source        TEXT,
    service       VARCHAR(255) NOT NULL,
    severity      severity_level NOT NULL,
    status        alert_status   NOT NULL DEFAULT 'firing',
    title         TEXT,
    message       TEXT NOT NULL,
    description   TEXT,
    labels        JSONB          NOT NULL DEFAULT '{}',
    annotations   JSONB          NOT NULL DEFAULT '{}',
    fingerprint   TEXT,
    fired_at      TIMESTAMPTZ,
    resolved_at   TIMESTAMPTZ,
    incident_id   UUID,
    timestamp     TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alerts_service_severity ON alerts.alerts(service, severity);
CREATE INDEX IF NOT EXISTS idx_alerts_status           ON alerts.alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_fingerprint      ON alerts.alerts(fingerprint);
CREATE INDEX IF NOT EXISTS idx_alerts_timestamp        ON alerts.alerts(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_incident_id      ON alerts.alerts(incident_id);
CREATE INDEX IF NOT EXISTS idx_alerts_created_at       ON alerts.alerts(created_at);

-- ── Alert Events (audit log) ────────────────────────────────
CREATE TABLE IF NOT EXISTS alerts.alert_events (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id    UUID             NOT NULL REFERENCES alerts.alerts(id) ON DELETE CASCADE,
    event_type  alert_event_type NOT NULL,
    payload     JSONB            NOT NULL DEFAULT '{}',
    created_at  TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_alert_events_alert ON alerts.alert_events(alert_id);

-- ── Incidents schema tables ─────────────────────────────────
CREATE TABLE IF NOT EXISTS incidents.incidents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id     VARCHAR(255) UNIQUE NOT NULL,
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    service         VARCHAR(255) NOT NULL,
    severity        severity_level  NOT NULL,
    status          incident_status NOT NULL DEFAULT 'open',
    assigned_to     UUID            REFERENCES users(id),
    notes           JSONB           NOT NULL DEFAULT '[]',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT now(),
    acknowledged_at TIMESTAMPTZ,
    resolved_at     TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_incidents_status   ON incidents.incidents(status);
CREATE INDEX IF NOT EXISTS idx_incidents_service  ON incidents.incidents(service);
CREATE INDEX IF NOT EXISTS idx_incidents_severity ON incidents.incidents(severity);
CREATE INDEX IF NOT EXISTS idx_incidents_created  ON incidents.incidents(created_at);

-- ── Incident ↔ Alerts (many-to-many) ────────────────────────
CREATE TABLE IF NOT EXISTS incidents.incident_alerts (
    incident_id UUID NOT NULL REFERENCES incidents.incidents(id) ON DELETE CASCADE,
    alert_id    UUID NOT NULL REFERENCES alerts.alerts(id)       ON DELETE CASCADE,
    linked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (incident_id, alert_id)
);

-- ── Notification Log ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS incidents.notification_log (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_id    UUID REFERENCES alerts.alerts(id),
    incident_id UUID REFERENCES incidents.incidents(id),
    user_id     UUID NOT NULL REFERENCES users(id),
    channel     notification_channel NOT NULL,
    status      notification_status  NOT NULL DEFAULT 'sent',
    sent_at     TIMESTAMPTZ          NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notif_alert    ON incidents.notification_log(alert_id);
CREATE INDEX IF NOT EXISTS idx_notif_incident ON incidents.notification_log(incident_id);

-- ── On-call schema tables ───────────────────────────────────
CREATE TABLE IF NOT EXISTS oncall.schedules (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team                VARCHAR(255) NOT NULL,
    rotation_type       VARCHAR(50)  NOT NULL,
    start_date          DATE         NOT NULL,
    engineers           JSONB        NOT NULL,
    escalation_minutes  INTEGER      DEFAULT 5,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS oncall.oncall_assignments (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_name   TEXT NOT NULL,
    user_id     UUID NOT NULL REFERENCES users(id),
    start_time  TIMESTAMPTZ NOT NULL,
    end_time    TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_oncall_team ON oncall.oncall_assignments(team_name);
CREATE INDEX IF NOT EXISTS idx_oncall_time ON oncall.oncall_assignments(start_time, end_time);

CREATE TABLE IF NOT EXISTS oncall.escalations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id     VARCHAR(255) NOT NULL,
    from_engineer   VARCHAR(255) NOT NULL,
    to_engineer     VARCHAR(255) NOT NULL,
    reason          VARCHAR(255),
    escalated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_escalations_incident ON oncall.escalations(incident_id);

-- ── Auto-update updated_at trigger ──────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_alerts_updated_at    ON alerts.alerts;
DROP TRIGGER IF EXISTS trg_incidents_updated_at ON incidents.incidents;

CREATE TRIGGER trg_alerts_updated_at
    BEFORE UPDATE ON alerts.alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER trg_incidents_updated_at
    BEFORE UPDATE ON incidents.incidents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ── Seed data ───────────────────────────────────────────────

-- Users for on-call rotations
INSERT INTO users (name, email, phone, role)
VALUES 
    ('Admin User', 'admin@example.com', '+1-555-0100', 'admin'),
    ('Alice Engineer', 'alice@example.com', '+1-555-0101', 'responder'),
    ('Bob Developer', 'bob@example.com', '+1-555-0102', 'responder'),
    ('Charlie SRE', 'charlie@example.com', '+1-555-0103', 'responder'),
    ('Diana Ops', 'diana@example.com', '+1-555-0104', 'responder'),
    ('Eve Backend', 'eve@example.com', '+1-555-0105', 'responder'),
    ('Frank Frontend', 'frank@example.com', '+1-555-0106', 'responder'),
    ('Grace DevOps', 'grace@example.com', '+1-555-0107', 'responder'),
    ('Henry Platform', 'henry@example.com', '+1-555-0108', 'responder')
ON CONFLICT (email) DO NOTHING;

-- On-call schedules for 3 teams (platform, backend, frontend)
INSERT INTO oncall.schedules (team, rotation_type, start_date, engineers, escalation_minutes)
VALUES 
    (
        'platform',
        'weekly',
        '2026-01-01',
        '[
            {"name": "Alice Engineer", "email": "alice@example.com", "primary": true},
            {"name": "Bob Developer", "email": "bob@example.com", "primary": false},
            {"name": "Charlie SRE", "email": "charlie@example.com", "primary": false}
        ]'::jsonb,
        5
    ),
    (
        'backend',
        'weekly',
        '2026-01-01',
        '[
            {"name": "Diana Ops", "email": "diana@example.com", "primary": true},
            {"name": "Eve Backend", "email": "eve@example.com", "primary": false}
        ]'::jsonb,
        10
    ),
    (
        'frontend',
        'daily',
        '2026-01-01',
        '[
            {"name": "Frank Frontend", "email": "frank@example.com", "primary": true},
            {"name": "Grace DevOps", "email": "grace@example.com", "primary": false},
            {"name": "Henry Platform", "email": "henry@example.com", "primary": false}
        ]'::jsonb,
        5
    )
ON CONFLICT DO NOTHING;
