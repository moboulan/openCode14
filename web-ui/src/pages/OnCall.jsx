import { useEffect, useState } from 'react';
import { getCurrentOncall, listSchedules } from '../services/api.js';

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
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        </span>
        <h2>Current On-Call</h2>
      </div>

      <div className="grid grid-3">
        {oncallList.map((item, idx) => (
          <div className="card" key={`${item.team}-${idx}`}>
            <div className="card-header">
              <h3 style={{ textTransform: 'uppercase' }}>{item.team}</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div className="metric-item">
                <span className="meta-label">Primary</span>
                <span className="meta-value">{item.primary}</span>
              </div>
              <div className="metric-item">
                <span className="meta-label">Secondary</span>
                <span className="meta-value">{item.secondary || '—'}</span>
              </div>
            </div>
          </div>
        ))}
        {oncallList.length === 0 && (
          <div className="card empty">No on-call teams configured.</div>
        )}
      </div>

      <div className="section-bar">
        <span className="icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
        </span>
        <h2>Schedules</h2>
      </div>

      <div className="card">
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
                  <td><span className="badge low" style={{ textTransform: 'uppercase' }}>{item.rotation_type}</span></td>
                  <td>{item.start_date}</td>
                  <td>{item.engineers.join(', ')}</td>
                  <td>{item.escalation_minutes}m</td>
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
