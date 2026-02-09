import { useState } from 'react';
import { formatDuration } from '../utils/formatters.js';

function Stat({ label, value, color }) {
  return (
    <div className={`stat-card${color ? ` ${color}` : ''}`}>
      <span className="stat-label">{label}</span>
      <span className="stat-value">{value}</span>
    </div>
  );
}

function IncidentAnalytics({ summary, byService = [] }) {
  const [showBreakdown, setShowBreakdown] = useState(false);

  if (!summary) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* ── Status + Response ── */}
      <div className="section-bar">
        <span className="icon">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 3v18h18"/><path d="M7 16l4-8 4 4 5-9"/></svg>
        </span>
        <h2>Metrics</h2>
      </div>

      <div className="grid grid-5">
        <Stat label="Total" value={summary.total ?? '—'} color="blue" />
        <Stat label="Open" value={summary.open_count ?? '—'} color="red" />
        <Stat label="Acknowledged" value={summary.ack_count ?? '—'} color="orange" />
        <Stat label="Resolved" value={summary.resolved_count ?? '—'} color="green" />
        <Stat label="Avg MTTA" value={formatDuration(summary.avg_mtta)} color="cyan" />
      </div>

      <div className="grid grid-4">
        <Stat label="Avg MTTR" value={formatDuration(summary.avg_mttr)} color="yellow" />
        <Stat label="Min MTTA" value={formatDuration(summary.min_mtta)} />
        <Stat label="Max MTTA" value={formatDuration(summary.max_mtta)} />
        <Stat label="Max MTTR" value={formatDuration(summary.max_mttr)} />
      </div>

      {/* ── By Service (collapsible) ── */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            className="collapse-toggle"
            onClick={() => setShowBreakdown(b => !b)}
          >
            <span className={`arrow${showBreakdown ? ' open' : ''}`}>▶</span>
            Service Breakdown ({byService.length})
          </button>
        </div>

        {showBreakdown && (
          <div className="table-wrap" style={{ marginTop: 10 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Incidents</th>
                  <th>Avg MTTA</th>
                  <th>Avg MTTR</th>
                </tr>
              </thead>
              <tbody>
                {byService.map((item) => (
                  <tr key={item.service}>
                    <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.service}</td>
                    <td>{item.count}</td>
                    <td>{formatDuration(item.avg_mtta)}</td>
                    <td>{formatDuration(item.avg_mttr)}</td>
                  </tr>
                ))}
                {byService.length === 0 && (
                  <tr><td colSpan="4" className="empty">No data available</td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default IncidentAnalytics;
