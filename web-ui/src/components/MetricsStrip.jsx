import { formatDuration } from '../utils/formatters.js';

/**
 * Tiny inline sparkline rendered as a pure SVG polyline.
 * Accepts an array of numbers and draws a 48×16 line chart.
 */
function Sparkline({ data = [], color = 'var(--text-muted)', width = 48, height = 16 }) {
  if (!data.length) return null;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const step = width / Math.max(data.length - 1, 1);
  const points = data
    .map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / range) * (height - 2) - 1).toFixed(1)}`)
    .join(' ');

  return (
    <svg width={width} height={height} className="status-bar__spark" style={{ display: 'block' }}>
      <polyline
        points={points}
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * High-density status bar that replaces the two rows of stat cards.
 *
 * Props:
 *   summary – analytics summary object (total, open_count, ack_count, etc.)
 *   mttaTrend – optional array of numbers for MTTA sparkline (last N values in seconds)
 *   mttrTrend – optional array of numbers for MTTR sparkline (last N values in seconds)
 */
function MetricsStrip({ summary, mttaTrend = [], mttrTrend = [] }) {
  if (!summary) return null;

  return (
    <div className="status-bar">
      {/* ── Incident counts ── */}
      <div className="status-bar__group">
        <div className="status-bar__item">
          <span className="status-bar__label">Total</span>
          <span className="status-bar__value">{summary.total ?? '—'}</span>
        </div>
        <div className="status-bar__item">
          <span className="status-bar__label">Open</span>
          <span className="status-bar__value red">{summary.open_count ?? '—'}</span>
        </div>
        <div className="status-bar__item">
          <span className="status-bar__label">Ack</span>
          <span className="status-bar__value orange">{summary.ack_count ?? '—'}</span>
        </div>
        <div className="status-bar__item">
          <span className="status-bar__label">Resolved</span>
          <span className="status-bar__value green">{summary.resolved_count ?? '—'}</span>
        </div>
      </div>

      <div className="status-bar__divider" />

      {/* ── Response timers ── */}
      <div className="status-bar__group">
        <div className="status-bar__item">
          <span className="status-bar__label">MTTA</span>
          <span className="status-bar__value cyan">{formatDuration(summary.avg_mtta)}</span>
          {mttaTrend.length > 1 && <Sparkline data={mttaTrend} color="var(--cyan)" />}
        </div>
        <div className="status-bar__item">
          <span className="status-bar__label">MTTR</span>
          <span className="status-bar__value yellow">{formatDuration(summary.avg_mttr)}</span>
          {mttrTrend.length > 1 && <Sparkline data={mttrTrend} color="var(--yellow)" />}
        </div>
      </div>

      <div className="status-bar__divider" />

      {/* ── Min/Max ── */}
      <div className="status-bar__group">
        <div className="status-bar__item">
          <span className="status-bar__label">Min MTTA</span>
          <span className="status-bar__value">{formatDuration(summary.min_mtta)}</span>
        </div>
        <div className="status-bar__item">
          <span className="status-bar__label">Max MTTA</span>
          <span className="status-bar__value">{formatDuration(summary.max_mtta)}</span>
        </div>
        <div className="status-bar__item">
          <span className="status-bar__label">Max MTTR</span>
          <span className="status-bar__value">{formatDuration(summary.max_mttr)}</span>
        </div>
      </div>
    </div>
  );
}

export default MetricsStrip;
