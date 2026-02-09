import { useEffect, useState } from 'react';
import { getCurrentOncall, listSchedules } from '../services/api.js';

function initials(email) {
  if (!email) return '?';
  const name = email.split('@')[0];
  const parts = name.split(/[._-]/);
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : name.slice(0, 2).toUpperCase();
}

function UserChip({ email, role }) {
  return (
    <div className="user-chip">
      <div className="user-chip__avatar">{initials(email)}</div>
      <div className="user-chip__info">
        <span className="user-chip__role">{role}</span>
        <span className="user-chip__email">{email}</span>
      </div>
    </div>
  );
}

function OnCall() {
  const [schedules, setSchedules] = useState([]);
  const [oncall, setOncall] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [schedResp, oncallResp] = await Promise.all([listSchedules(), getCurrentOncall()]);
        setSchedules(schedResp.schedules ?? []);
        setOncall(oncallResp);
      } catch {
        setError('Failed to load on-call data');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const oncallList = oncall ? (Array.isArray(oncall.oncall) ? oncall.oncall : [oncall]) : [];

  if (loading) return <p className="loading-text">Loading on-call data…</p>;

  return (
    <div className="page">
      {error && <div className="error-banner">{error}</div>}

      <div className="section-bar">
        <span className="icon">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </span>
        <h2>Current On-Call</h2>
      </div>

      {/* Roster Grid */}
      <div className="roster-grid">
        {oncallList.map((item, idx) => (
          <div className="roster-card" key={`${item.team}-${idx}`}>
            <div className="roster-card__team">{item.team}</div>
            <UserChip email={item.primary} role="Primary" />
            {item.secondary && <UserChip email={item.secondary} role="Secondary" />}
          </div>
        ))}
        {oncallList.length === 0 && (
          <div className="card empty">No on-call teams configured.</div>
        )}
      </div>

      <div className="section-bar">
        <span className="icon">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        </span>
        <h2>Schedules</h2>
      </div>

      <div className="card" style={{ padding: '4px 0' }}>
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Team</th>
                <th>Rotation</th>
                <th>Start</th>
                <th>Engineers</th>
                <th>Escalation</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((item) => (
                <tr key={item.id}>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.team}</td>
                  <td>
                    <span className={`badge-rotation ${item.rotation_type}`}>
                      {item.rotation_type}
                    </span>
                  </td>
                  <td><span className="mono">{item.start_date}</span></td>
                  <td style={{ color: 'var(--text-muted)' }}>{item.engineers.join(', ')}</td>
                  <td><span className="mono">{item.escalation_minutes}m</span></td>
                </tr>
              ))}
              {schedules.length === 0 && (
                <tr><td colSpan="5" className="empty">No schedules found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default OnCall;
