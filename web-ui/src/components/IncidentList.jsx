import { Link } from 'react-router-dom';
import { useState, useMemo } from 'react';
import { formatDateTime } from '../utils/formatters.js';

function SeverityBadge({ severity }) {
  return <span className={`badge ${severity ?? ''}`}>{severity}</span>;
}

function StatusChip({ status }) {
  return <span className={`status-chip ${status ?? ''}`}>{status}</span>;
}

const STATUSES = ['all', 'open', 'acknowledged', 'resolved'];
const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low'];

function IncidentList({ incidents = [], total }) {
  const [statusFilter, setStatusFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [sortKey, setSortKey] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');

  const filtered = useMemo(() => {
    let list = [...incidents];
    if (statusFilter !== 'all') list = list.filter(i => i.status === statusFilter);
    if (severityFilter !== 'all') list = list.filter(i => i.severity === severityFilter);

    const sevOrder = { critical: 0, high: 1, medium: 2, low: 3 };
    list.sort((a, b) => {
      let aVal, bVal;
      if (sortKey === 'severity') {
        aVal = sevOrder[a.severity] ?? 9;
        bVal = sevOrder[b.severity] ?? 9;
      } else if (sortKey === 'created_at') {
        aVal = new Date(a.created_at).getTime();
        bVal = new Date(b.created_at).getTime();
      } else {
        aVal = (a[sortKey] || '').toString().toLowerCase();
        bVal = (b[sortKey] || '').toString().toLowerCase();
      }
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
    return list;
  }, [incidents, statusFilter, severityFilter, sortKey, sortDir]);

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const statusCounts = useMemo(() => {
    const c = { open: 0, acknowledged: 0, resolved: 0 };
    incidents.forEach(i => { if (c[i.status] !== undefined) c[i.status]++; });
    return c;
  }, [incidents]);

  const sevCounts = useMemo(() => {
    const c = { critical: 0, high: 0, medium: 0, low: 0 };
    incidents.forEach(i => { if (c[i.severity] !== undefined) c[i.severity]++; });
    return c;
  }, [incidents]);

  const SortArrow = ({ col }) => {
    if (sortKey !== col) return <span style={{ opacity: 0.2, marginLeft: 3 }}>↕</span>;
    return <span style={{ marginLeft: 3 }}>{sortDir === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <>
      <div className="section-bar">
        <span className="icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        </span>
        <h2>Incidents</h2>
        <span className="sev-dots">
          {sevCounts.critical > 0 && <span className="sev-dot" style={{ color: 'var(--red)' }}>● {sevCounts.critical}</span>}
          {sevCounts.high > 0 && <span className="sev-dot" style={{ color: 'var(--orange)' }}>● {sevCounts.high}</span>}
          {sevCounts.medium > 0 && <span className="sev-dot" style={{ color: 'var(--yellow)' }}>● {sevCounts.medium}</span>}
          {sevCounts.low > 0 && <span className="sev-dot" style={{ color: 'var(--green)' }}>● {sevCounts.low}</span>}
        </span>
        <div className="section-right">
          <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>
            {filtered.length}/{total ?? incidents.length}
          </span>
        </div>
      </div>

      <div className="card">
        <div style={{ display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', marginBottom: 14 }}>
          <div className="filter-bar">
            <span className="filter-label">Status</span>
            {STATUSES.map(s => (
              <button
                key={s}
                className={`filter-btn${statusFilter === s ? ' active' : ''}`}
                onClick={() => setStatusFilter(s)}
              >
                {s === 'all' ? 'All' : s}
                {s !== 'all' && <span className="filter-count">({statusCounts[s] || 0})</span>}
              </button>
            ))}
          </div>
          <div style={{ width: 1, height: 20, background: 'var(--border)' }} />
          <div className="filter-bar">
            <span className="filter-label">Severity</span>
            {SEVERITIES.map(s => (
              <button
                key={s}
                className={`filter-btn${severityFilter === s ? ' active' : ''}`}
                onClick={() => setSeverityFilter(s)}
              >
                {s === 'all' ? 'All' : s}
              </button>
            ))}
          </div>
        </div>

        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('title')}>
                  Title <SortArrow col="title" />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('service')}>
                  Service <SortArrow col="service" />
                </th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('severity')}>
                  Severity <SortArrow col="severity" />
                </th>
                <th>Status</th>
                <th>Assigned</th>
                <th style={{ cursor: 'pointer' }} onClick={() => handleSort('created_at')}>
                  Created <SortArrow col="created_at" />
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((incident) => (
                <tr key={incident.incident_id} className="clickable">
                  <td>
                    <Link to={`/incidents/${incident.incident_id}`}>{incident.title}</Link>
                  </td>
                  <td>{incident.service}</td>
                  <td><SeverityBadge severity={incident.severity} /></td>
                  <td><StatusChip status={incident.status} /></td>
                  <td>{incident.assigned_to || '—'}</td>
                  <td style={{ whiteSpace: 'nowrap' }}><span className="mono">{formatDateTime(incident.created_at)}</span></td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan="6" className="empty">No incidents match the current filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}

export default IncidentList;
