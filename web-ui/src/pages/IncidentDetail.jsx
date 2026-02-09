import { useEffect, useCallback, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getIncident, getIncidentMetrics, updateIncident, addIncidentNote } from '../services/api.js';
import { formatDateTime, formatDuration } from '../utils/formatters.js';

function Timeline({ events = [] }) {
  if (!events.length) return <p className="loading-text">No timeline yet.</p>;
  return (
    <ul className="timeline-list">
      {events.map((item, idx) => (
        <li key={`${item.event}-${idx}`} className="timeline-item">
          <span className="tl-event">{item.event}</span>
          <span className="tl-time">{formatDateTime(item.timestamp)}</span>
        </li>
      ))}
    </ul>
  );
}

function AlertList({ alerts = [] }) {
  if (!alerts.length) return <p className="loading-text">No linked alerts.</p>;
  return (
    <ul className="list">
      {alerts.map((alert) => (
        <li key={alert.alert_id}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: 13 }}>{alert.message}</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {alert.service} · <span className={`badge ${alert.severity}`} style={{ fontSize: 10, padding: '1px 6px' }}>{alert.severity}</span> · {formatDateTime(alert.timestamp)}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function NotesList({ notes = [] }) {
  if (!notes.length) return <p className="loading-text">No notes yet.</p>;
  return (
    <ul className="list">
      {notes.map((note, idx) => (
        <li key={idx}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <span style={{ color: 'var(--text-primary)', fontSize: 13 }}>{note.content}</span>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {note.author} · {formatDateTime(note.created_at)}
            </span>
          </div>
        </li>
      ))}
    </ul>
  );
}

function IncidentDetail() {
  const { incidentId } = useParams();
  const [incident, setIncident] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionStatus, setActionStatus] = useState('');
  const [activeTab, setActiveTab] = useState('timeline');
  const [noteText, setNoteText] = useState('');

  const loadIncident = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getIncident(incidentId);
      setIncident(data);
      setError(null);
    } catch {
      setError('Incident not found');
    } finally {
      setLoading(false);
    }
  }, [incidentId]);

  const loadMetrics = useCallback(async () => {
    try {
      const data = await getIncidentMetrics(incidentId);
      setMetrics(data);
    } catch { /* skip */ }
  }, [incidentId]);

  useEffect(() => {
    loadIncident();
    loadMetrics();
  }, [loadIncident, loadMetrics]);

  const handleUpdate = async (status) => {
    try {
      setActionStatus('Saving…');
      const updated = await updateIncident(incidentId, { status });
      setIncident(updated);
      loadMetrics();
      setActionStatus('');
    } catch {
      setActionStatus('Failed to update');
    }
  };

  const handleAddNote = async () => {
    if (!noteText.trim()) return;
    try {
      await addIncidentNote(incidentId, { content: noteText.trim(), author: 'operator' });
      setNoteText('');
      loadIncident();
    } catch { /* skip */ }
  };

  if (loading && !incident) return <p className="loading-text">Loading incident…</p>;
  if (error) return <div className="error-banner">{error}</div>;
  if (!incident) return null;

  const tabs = [
    { key: 'timeline', label: 'Timeline', count: incident.timeline?.length },
    { key: 'alerts', label: 'Alerts', count: incident.alerts?.length },
    { key: 'notes', label: 'Notes', count: incident.notes?.length },
  ];

  return (
    <div className="page">
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <Link to="/">Dashboard</Link>
        <span className="sep">/</span>
        <span className="current">{incident.incident_id}</span>
      </div>

      {/* Header */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: 260 }}>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 700, color: 'var(--text-primary)' }}>{incident.title}</h2>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8, flexWrap: 'wrap' }}>
              <span className={`badge ${incident.severity}`}>{incident.severity}</span>
              <span className={`status-chip ${incident.status}`}>{incident.status}</span>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>·</span>
              <span style={{ fontSize: 13, color: 'var(--text-secondary)', fontWeight: 600 }}>{incident.service}</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => handleUpdate('acknowledged')}
              disabled={incident.status === 'acknowledged' || incident.status === 'resolved'}
            >
              Acknowledge
            </button>
            <button
              className="btn-danger"
              onClick={() => handleUpdate('resolved')}
              disabled={incident.status === 'resolved'}
            >
              Resolve
            </button>
          </div>
        </div>

        <div className="metric-grid" style={{ marginTop: 16 }}>
          <div className="metric-item">
            <span className="meta-label">Assigned To</span>
            <span className="meta-value">{incident.assigned_to || 'Unassigned'}</span>
          </div>
          <div className="metric-item">
            <span className="meta-label">Created</span>
            <span className="meta-value">{formatDateTime(incident.created_at)}</span>
          </div>
          <div className="metric-item">
            <span className="meta-label">Acknowledged</span>
            <span className="meta-value">{formatDateTime(incident.acknowledged_at)}</span>
          </div>
          <div className="metric-item">
            <span className="meta-label">Resolved</span>
            <span className="meta-value">{formatDateTime(incident.resolved_at)}</span>
          </div>
        </div>
        {actionStatus && <p style={{ marginTop: 8, fontSize: 11, color: 'var(--text-muted)' }}>{actionStatus}</p>}
      </div>

      {/* Response Metrics */}
      {metrics && (
        <div className="grid grid-4">
          <div className="stat-card cyan">
            <span className="stat-label">MTTA</span>
            <span className="stat-value">{formatDuration(metrics.mtta_seconds)}</span>
          </div>
          <div className="stat-card yellow">
            <span className="stat-label">MTTR</span>
            <span className="stat-value">{formatDuration(metrics.mttr_seconds)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Created</span>
            <span className="stat-value" style={{ fontSize: 13 }}>{formatDateTime(metrics.created_at)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-label">Resolved</span>
            <span className="stat-value" style={{ fontSize: 13 }}>{formatDateTime(metrics.resolved_at)}</span>
          </div>
        </div>
      )}

      {/* Tabbed Content */}
      <div className="card" style={{ padding: 0 }}>
        <div className="tabs">
          {tabs.map(t => (
            <button
              key={t.key}
              className={`tab${activeTab === t.key ? ' active' : ''}`}
              onClick={() => setActiveTab(t.key)}
            >
              {t.label} {t.count != null && <span style={{ opacity: 0.5 }}>({t.count})</span>}
            </button>
          ))}
        </div>

        <div style={{ padding: 20 }}>
          {activeTab === 'timeline' && <Timeline events={incident.timeline} />}
          {activeTab === 'alerts' && <AlertList alerts={incident.alerts} />}
          {activeTab === 'notes' && (
            <div>
              <NotesList notes={incident.notes} />
              <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                <input
                  type="text"
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddNote()}
                  placeholder="Add a note…"
                  style={{
                    flex: 1,
                    background: 'var(--bg-input)',
                    border: '1px solid var(--border)',
                    borderRadius: '6px',
                    color: 'var(--text-primary)',
                    padding: '8px 12px',
                    fontSize: 13,
                    fontFamily: 'var(--font)',
                  }}
                />
                <button className="btn-primary" onClick={handleAddNote} disabled={!noteText.trim()}>
                  Add
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default IncidentDetail;
