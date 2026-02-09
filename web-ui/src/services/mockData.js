// ─── Mock data store for testing UI interactions ───

const now = new Date('2026-02-09T10:00:00Z');
const ts = (minOffset) => new Date(now.getTime() + minOffset * 60000).toISOString();

// ── Alerts ──────────────────────────────────────────
let alerts = [
  {
    alert_id: 'alert-a1b2c3d4e5f6',
    service: 'payment-api',
    severity: 'critical',
    message: 'Error rate exceeded 25% threshold',
    labels: { env: 'prod', region: 'us-east-1' },
    timestamp: ts(-120),
    incident_id: 'inc-0001',
    created_at: ts(-120),
  },
  {
    alert_id: 'alert-b2c3d4e5f6a7',
    service: 'payment-api',
    severity: 'critical',
    message: 'p99 latency > 2 s for /checkout',
    labels: { env: 'prod', region: 'us-east-1' },
    timestamp: ts(-115),
    incident_id: 'inc-0001',
    created_at: ts(-115),
  },
  {
    alert_id: 'alert-c3d4e5f6a7b8',
    service: 'auth-service',
    severity: 'high',
    message: 'JWT validation failures spiking',
    labels: { env: 'prod' },
    timestamp: ts(-90),
    incident_id: 'inc-0002',
    created_at: ts(-90),
  },
  {
    alert_id: 'alert-d4e5f6a7b8c9',
    service: 'user-service',
    severity: 'medium',
    message: 'Database connection pool at 85%',
    labels: { env: 'prod', db: 'postgres-primary' },
    timestamp: ts(-60),
    incident_id: 'inc-0003',
    created_at: ts(-60),
  },
  {
    alert_id: 'alert-e5f6a7b8c9d0',
    service: 'search-service',
    severity: 'low',
    message: 'Index rebuild slower than usual',
    labels: { env: 'staging' },
    timestamp: ts(-45),
    incident_id: null,
    created_at: ts(-45),
  },
  {
    alert_id: 'alert-f6a7b8c9d0e1',
    service: 'notification-service',
    severity: 'high',
    message: 'Email delivery queue backlog > 5 000',
    labels: { env: 'prod', provider: 'ses' },
    timestamp: ts(-30),
    incident_id: 'inc-0004',
    created_at: ts(-30),
  },
  {
    alert_id: 'alert-g7b8c9d0e1f2',
    service: 'payment-api',
    severity: 'critical',
    message: 'Stripe webhook failures > 10/min',
    labels: { env: 'prod' },
    timestamp: ts(-15),
    incident_id: 'inc-0005',
    created_at: ts(-15),
  },
  {
    alert_id: 'alert-h8c9d0e1f2g3',
    service: 'api-gateway',
    severity: 'medium',
    message: 'Rate-limiter triggering for /api/v2/*',
    labels: { env: 'prod' },
    timestamp: ts(-10),
    incident_id: 'inc-0006',
    created_at: ts(-10),
  },
  {
    alert_id: 'alert-i9d0e1f2g3h4',
    service: 'inventory-service',
    severity: 'high',
    message: 'Stock sync mismatch detected (42 SKUs)',
    labels: { env: 'prod', warehouse: 'wh-02' },
    timestamp: ts(-5),
    incident_id: 'inc-0007',
    created_at: ts(-5),
  },
  {
    alert_id: 'alert-j0e1f2g3h4i5',
    service: 'cdn-edge',
    severity: 'low',
    message: 'Cache hit ratio dropped below 90%',
    labels: { env: 'prod', pop: 'cdg-1' },
    timestamp: ts(-2),
    incident_id: null,
    created_at: ts(-2),
  },
];

// ── Incidents ───────────────────────────────────────
let incidents = [
  {
    incident_id: 'inc-0001',
    title: 'Payment API High Error Rate',
    service: 'payment-api',
    severity: 'critical',
    status: 'open',
    assigned_to: 'alice@company.com',
    created_at: ts(-120),
    acknowledged_at: null,
    resolved_at: null,
    mtta_seconds: null,
    mttr_seconds: null,
    notes: [],
    alerts: alerts.filter((a) => a.incident_id === 'inc-0001'),
    timeline: [{ event: 'created', timestamp: ts(-120) }],
  },
  {
    incident_id: 'inc-0002',
    title: 'Auth Service JWT Failures',
    service: 'auth-service',
    severity: 'high',
    status: 'acknowledged',
    assigned_to: 'bob@company.com',
    created_at: ts(-90),
    acknowledged_at: ts(-85),
    resolved_at: null,
    mtta_seconds: 300,
    mttr_seconds: null,
    notes: ['Investigating token rotation issue'],
    alerts: alerts.filter((a) => a.incident_id === 'inc-0002'),
    timeline: [
      { event: 'created', timestamp: ts(-90) },
      { event: 'acknowledged', timestamp: ts(-85) },
    ],
  },
  {
    incident_id: 'inc-0003',
    title: 'User Service DB Pool Exhaustion',
    service: 'user-service',
    severity: 'medium',
    status: 'resolved',
    assigned_to: 'charlie@company.com',
    created_at: ts(-60),
    acknowledged_at: ts(-55),
    resolved_at: ts(-20),
    mtta_seconds: 300,
    mttr_seconds: 2400,
    notes: ['Increased pool size to 50', 'Root cause: leaked connections in batch job'],
    alerts: alerts.filter((a) => a.incident_id === 'inc-0003'),
    timeline: [
      { event: 'created', timestamp: ts(-60) },
      { event: 'acknowledged', timestamp: ts(-55) },
      { event: 'resolved', timestamp: ts(-20) },
    ],
  },
  {
    incident_id: 'inc-0004',
    title: 'Email Delivery Queue Backlog',
    service: 'notification-service',
    severity: 'high',
    status: 'open',
    assigned_to: 'diana@company.com',
    created_at: ts(-30),
    acknowledged_at: null,
    resolved_at: null,
    mtta_seconds: null,
    mttr_seconds: null,
    notes: [],
    alerts: alerts.filter((a) => a.incident_id === 'inc-0004'),
    timeline: [{ event: 'created', timestamp: ts(-30) }],
  },
  {
    incident_id: 'inc-0005',
    title: 'Stripe Webhook Processing Failures',
    service: 'payment-api',
    severity: 'critical',
    status: 'acknowledged',
    assigned_to: 'alice@company.com',
    created_at: ts(-15),
    acknowledged_at: ts(-12),
    resolved_at: null,
    mtta_seconds: 180,
    mttr_seconds: null,
    notes: ['Stripe status page shows degraded API'],
    alerts: alerts.filter((a) => a.incident_id === 'inc-0005'),
    timeline: [
      { event: 'created', timestamp: ts(-15) },
      { event: 'acknowledged', timestamp: ts(-12) },
    ],
  },
  {
    incident_id: 'inc-0006',
    title: 'API Gateway Rate Limiting Spike',
    service: 'api-gateway',
    severity: 'medium',
    status: 'open',
    assigned_to: 'bob@company.com',
    created_at: ts(-10),
    acknowledged_at: null,
    resolved_at: null,
    mtta_seconds: null,
    mttr_seconds: null,
    notes: [],
    alerts: alerts.filter((a) => a.incident_id === 'inc-0006'),
    timeline: [{ event: 'created', timestamp: ts(-10) }],
  },
  {
    incident_id: 'inc-0007',
    title: 'Inventory Stock Sync Mismatch',
    service: 'inventory-service',
    severity: 'high',
    status: 'open',
    assigned_to: 'charlie@company.com',
    created_at: ts(-5),
    acknowledged_at: null,
    resolved_at: null,
    mtta_seconds: null,
    mttr_seconds: null,
    notes: [],
    alerts: alerts.filter((a) => a.incident_id === 'inc-0007'),
    timeline: [{ event: 'created', timestamp: ts(-5) }],
  },
];

// ── Schedules / On-Call ─────────────────────────────
const schedules = [
  {
    id: 1,
    team: 'platform',
    rotation_type: 'daily',
    start_date: '2026-02-01',
    engineers: ['alice@company.com', 'bob@company.com'],
    escalation_minutes: 5,
    created_at: '2026-02-01T00:00:00Z',
  },
  {
    id: 2,
    team: 'backend',
    rotation_type: 'weekly',
    start_date: '2026-02-01',
    engineers: ['charlie@company.com', 'diana@company.com'],
    escalation_minutes: 10,
    created_at: '2026-02-01T00:00:00Z',
  },
  {
    id: 3,
    team: 'infra',
    rotation_type: 'daily',
    start_date: '2026-02-03',
    engineers: ['eve@company.com', 'frank@company.com', 'grace@company.com'],
    escalation_minutes: 3,
    created_at: '2026-02-03T00:00:00Z',
  },
];

const oncallCurrent = {
  oncall: [
    { team: 'platform', primary: 'alice@company.com', secondary: 'bob@company.com' },
    { team: 'backend', primary: 'charlie@company.com', secondary: 'diana@company.com' },
    { team: 'infra', primary: 'eve@company.com', secondary: 'frank@company.com' },
  ],
};

// ── Notifications ───────────────────────────────────
const notifications = [
  { notification_id: 'notif-001', incident_id: 'inc-0001', engineer: 'alice@company.com', channel: 'mock', message: 'New critical incident: Payment API High Error Rate', status: 'sent', created_at: ts(-120) },
  { notification_id: 'notif-002', incident_id: 'inc-0002', engineer: 'bob@company.com', channel: 'mock', message: 'New high incident: Auth Service JWT Failures', status: 'sent', created_at: ts(-90) },
  { notification_id: 'notif-003', incident_id: 'inc-0003', engineer: 'charlie@company.com', channel: 'mock', message: 'New medium incident: User Service DB Pool Exhaustion', status: 'sent', created_at: ts(-60) },
  { notification_id: 'notif-004', incident_id: 'inc-0004', engineer: 'diana@company.com', channel: 'mock', message: 'New high incident: Email Delivery Queue Backlog', status: 'sent', created_at: ts(-30) },
  { notification_id: 'notif-005', incident_id: 'inc-0005', engineer: 'alice@company.com', channel: 'mock', message: 'New critical incident: Stripe Webhook Processing Failures', status: 'sent', created_at: ts(-15) },
];

// ── Analytics (derived) ─────────────────────────────
function computeAnalytics() {
  const resolved = incidents.filter((i) => i.status === 'resolved');
  const withMtta = incidents.filter((i) => i.mtta_seconds !== null);
  const withMttr = resolved.filter((i) => i.mttr_seconds !== null);

  const avg = (arr, key) => arr.length ? arr.reduce((s, i) => s + i[key], 0) / arr.length : null;
  const min = (arr, key) => arr.length ? Math.min(...arr.map((i) => i[key])) : null;
  const max = (arr, key) => arr.length ? Math.max(...arr.map((i) => i[key])) : null;

  const services = [...new Set(incidents.map((i) => i.service))];

  return {
    summary: {
      total: incidents.length,
      open_count: incidents.filter((i) => i.status === 'open').length,
      ack_count: incidents.filter((i) => i.status === 'acknowledged').length,
      resolved_count: resolved.length,
      avg_mtta: avg(withMtta, 'mtta_seconds'),
      avg_mttr: avg(withMttr, 'mttr_seconds'),
      min_mtta: min(withMtta, 'mtta_seconds'),
      max_mtta: max(withMtta, 'mtta_seconds'),
      min_mttr: min(withMttr, 'mttr_seconds'),
      max_mttr: max(withMttr, 'mttr_seconds'),
    },
    by_service: services.map((svc) => {
      const svcInc = incidents.filter((i) => i.service === svc);
      const svcMtta = svcInc.filter((i) => i.mtta_seconds !== null);
      const svcMttr = svcInc.filter((i) => i.mttr_seconds !== null);
      return {
        service: svc,
        count: svcInc.length,
        avg_mtta: avg(svcMtta, 'mtta_seconds'),
        avg_mttr: avg(svcMttr, 'mttr_seconds'),
      };
    }),
  };
}

// ── Helpers ─────────────────────────────────────────
const delay = (ms = 150) => new Promise((r) => setTimeout(r, ms));
let alertCounter = alerts.length;
let notifCounter = notifications.length;

// ── Trend data (simulated 14-day history) ───────────
function computeTrends() {
  // Seed a deterministic random using simple hash
  const seed = (n) => ((n * 9301 + 49297) % 233280) / 233280;
  const days = 14;
  const trends = [];
  for (let i = days - 1; i >= 0; i--) {
    const date = new Date(now.getTime() - i * 86400000);
    const s = seed(i + 7);
    const s2 = seed(i + 42);
    trends.push({
      date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      mtta: Math.round(120 + s * 480),       // 2–10 min range
      mttr: Math.round(900 + s2 * 4500),     // 15–90 min range
      incidents: Math.round(1 + s * 6),
    });
  }
  return trends;
}

function computeTrendsByService() {
  const services = [...new Set(incidents.map((i) => i.service))];
  const seed = (n) => ((n * 9301 + 49297) % 233280) / 233280;
  return services.map((svc, sIdx) => {
    const points = [];
    for (let i = 13; i >= 0; i--) {
      const date = new Date(now.getTime() - i * 86400000);
      const s = seed(i + sIdx * 13 + 5);
      const s2 = seed(i + sIdx * 7 + 19);
      points.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        mtta: Math.round(90 + s * 540),
        mttr: Math.round(600 + s2 * 5400),
      });
    }
    return { service: svc, data: points };
  });
}

// ── Public mock API ─────────────────────────────────

// Alerts
export async function listAlerts(params = {}) {
  await delay();
  let result = [...alerts];
  if (params.service) result = result.filter((a) => a.service === params.service);
  if (params.severity) result = result.filter((a) => a.severity === params.severity);
  const limit = Math.min(params.limit || 100, 1000);
  result = result.slice(0, limit);
  return { alerts: result, total: result.length };
}

export async function createAlert(payload) {
  await delay();
  alertCounter++;
  const alert = {
    alert_id: `alert-mock-${String(alertCounter).padStart(4, '0')}`,
    service: payload.service,
    severity: payload.severity,
    message: payload.message,
    labels: payload.labels || {},
    timestamp: payload.timestamp || new Date().toISOString(),
    incident_id: null,
    created_at: new Date().toISOString(),
  };
  alerts.unshift(alert);
  return { alert_id: alert.alert_id, incident_id: null, status: 'processed', action: 'new_incident', timestamp: alert.created_at };
}

export async function getAlert(alertId) {
  await delay();
  const alert = alerts.find((a) => a.alert_id === alertId);
  if (!alert) throw { response: { status: 404, data: { detail: 'Alert not found' } } };
  return alert;
}

// Incidents
export async function listIncidents(params = {}) {
  await delay();
  let result = [...incidents];
  if (params.status) result = result.filter((i) => i.status === params.status);
  if (params.severity) result = result.filter((i) => i.severity === params.severity);
  if (params.service) result = result.filter((i) => i.service === params.service);
  const limit = Math.min(params.limit || 100, 1000);
  result = result.slice(0, limit);
  return { incidents: result, total: result.length };
}

export async function createIncident(payload) {
  await delay();
  const incident = {
    incident_id: `inc-mock-${String(incidents.length + 1).padStart(4, '0')}`,
    title: payload.title,
    service: payload.service,
    severity: payload.severity,
    status: 'open',
    assigned_to: payload.assigned_to || 'alice@company.com',
    created_at: new Date().toISOString(),
    acknowledged_at: null,
    resolved_at: null,
    mtta_seconds: null,
    mttr_seconds: null,
    notes: [],
    alerts: [],
    timeline: [{ event: 'created', timestamp: new Date().toISOString() }],
  };
  incidents.unshift(incident);
  return incident;
}

export async function getIncident(incidentId) {
  await delay();
  const incident = incidents.find((i) => i.incident_id === incidentId);
  if (!incident) throw { response: { status: 404, data: { detail: 'Incident not found' } } };
  return { ...incident };
}

export async function updateIncident(incidentId, payload) {
  await delay();
  const incident = incidents.find((i) => i.incident_id === incidentId);
  if (!incident) throw { response: { status: 404, data: { detail: 'Incident not found' } } };

  const nowStr = new Date().toISOString();

  if (payload.status === 'acknowledged' && incident.status === 'open') {
    incident.status = 'acknowledged';
    incident.acknowledged_at = nowStr;
    incident.mtta_seconds = (new Date(nowStr) - new Date(incident.created_at)) / 1000;
    incident.timeline.push({ event: 'acknowledged', timestamp: nowStr });
  }

  if (payload.status === 'resolved' && incident.status !== 'resolved') {
    if (!incident.acknowledged_at) {
      incident.acknowledged_at = nowStr;
      incident.mtta_seconds = (new Date(nowStr) - new Date(incident.created_at)) / 1000;
      incident.timeline.push({ event: 'acknowledged', timestamp: nowStr });
    }
    incident.status = 'resolved';
    incident.resolved_at = nowStr;
    incident.mttr_seconds = (new Date(nowStr) - new Date(incident.created_at)) / 1000;
    incident.timeline.push({ event: 'resolved', timestamp: nowStr });
  }

  if (payload.assigned_to) {
    incident.assigned_to = payload.assigned_to;
    incident.timeline.push({ event: 'reassigned', timestamp: nowStr });
  }

  if (payload.notes && payload.notes.length) {
    incident.notes.push(...payload.notes);
  }

  return { ...incident };
}

export async function getIncidentAnalytics() {
  await delay();
  return computeAnalytics();
}

export async function getIncidentMetrics(incidentId) {
  await delay();
  const incident = incidents.find((i) => i.incident_id === incidentId);
  if (!incident) throw { response: { status: 404, data: { detail: 'Incident not found' } } };
  return {
    incident_id: incident.incident_id,
    mtta_seconds: incident.mtta_seconds,
    mttr_seconds: incident.mttr_seconds,
    created_at: incident.created_at,
    acknowledged_at: incident.acknowledged_at,
    resolved_at: incident.resolved_at,
  };
}

export async function addIncidentNote(incidentId, payload) {
  await delay();
  const incident = incidents.find((i) => i.incident_id === incidentId);
  if (!incident) throw { response: { status: 404, data: { detail: 'Incident not found' } } };
  const note = { content: payload.content, author: payload.author || 'operator', created_at: new Date().toISOString() };
  if (!incident.notes) incident.notes = [];
  incident.notes.push(note);
  return note;
}

// On-Call
export async function listSchedules() {
  await delay();
  return { schedules, total: schedules.length };
}

export async function getCurrentOncall(params = {}) {
  await delay();
  if (params.team) {
    const entry = oncallCurrent.oncall.find((o) => o.team === params.team);
    return entry || { team: params.team, primary: 'unassigned', secondary: null, escalation_minutes: 5 };
  }
  return oncallCurrent;
}

export async function escalateIncident(payload) {
  await delay();
  const incident = incidents.find((i) => i.incident_id === payload.incident_id);
  if (!incident) throw { response: { status: 404, data: { detail: 'Incident not found' } } };
  const from = incident.assigned_to;
  const team = oncallCurrent.oncall.find((o) => o.primary === from || o.secondary === from);
  const to = team ? (team.primary === from ? team.secondary : team.primary) : 'unassigned';
  incident.assigned_to = to;
  incident.timeline.push({ event: 'escalated', timestamp: new Date().toISOString() });
  return {
    incident_id: incident.incident_id,
    escalated_from: from,
    escalated_to: to,
    reason: payload.reason || 'Escalation timeout',
    timestamp: new Date().toISOString(),
  };
}

// Notifications
export async function listNotifications(params = {}) {
  await delay();
  let result = [...notifications];
  if (params.incident_id) result = result.filter((n) => n.incident_id === params.incident_id);
  if (params.engineer) result = result.filter((n) => n.engineer === params.engineer);
  const limit = Math.min(params.limit || 100, 1000);
  result = result.slice(0, limit);
  return { notifications: result, total: result.length };
}

export async function sendNotification(payload) {
  await delay();
  notifCounter++;
  const notif = {
    notification_id: `notif-mock-${String(notifCounter).padStart(3, '0')}`,
    incident_id: payload.incident_id || null,
    engineer: payload.engineer,
    channel: payload.channel || 'mock',
    message: payload.message,
    status: 'sent',
    created_at: new Date().toISOString(),
  };
  notifications.unshift(notif);
  return notif;
}

// Metrics Trends
export async function getMetricsTrends() {
  await delay();
  return {
    trends: computeTrends(),
    by_service: computeTrendsByService(),
  };
}
