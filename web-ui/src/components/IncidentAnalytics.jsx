import { useState } from 'react';
import MetricsStrip from './MetricsStrip.jsx';
import { formatDuration } from '../utils/formatters.js';

function IncidentAnalytics({ summary, byService = [], mttaTrend = [], mttrTrend = [] }) {
  const [showBreakdown, setShowBreakdown] = useState(false);

  if (!summary) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      <MetricsStrip summary={summary} mttaTrend={mttaTrend} mttrTrend={mttrTrend} />

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
          <div className="table-wrap" style={{ marginTop: 6 }}>
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
                    <td><span className="mono">{item.count}</span></td>
                    <td><span className="mono">{formatDuration(item.avg_mtta)}</span></td>
                    <td><span className="mono">{formatDuration(item.avg_mttr)}</span></td>
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
