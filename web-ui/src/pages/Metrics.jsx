import { useEffect, useCallback, useState } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar,
} from 'recharts';
import IncidentAnalytics from '../components/IncidentAnalytics.jsx';
import { getIncidentAnalytics, getMetricsTrends } from '../services/api.js';
import { formatDuration } from '../utils/formatters.js';

const COLORS = ['#111827', '#dc2626', '#ea580c', '#0891b2', '#16a34a', '#ca8a04'];

function CustomTooltip({ active, payload, label, valueFormatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{
      background: '#fff',
      border: '1px solid #e5e7eb',
      borderRadius: 8,
      padding: '10px 14px',
      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
      fontSize: 13,
    }}>
      <div style={{ fontWeight: 600, marginBottom: 6, color: '#111827' }}>{label}</div>
      {payload.map((entry, idx) => (
        <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#6b7280', marginBottom: 2 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: entry.color, flexShrink: 0 }} />
          <span>{entry.name}:</span>
          <span style={{ fontWeight: 600, color: '#111827', fontFamily: 'var(--font-mono)' }}>
            {valueFormatter ? valueFormatter(entry.value) : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

function Metrics() {
  const [data, setData] = useState(null);
  const [trends, setTrends] = useState(null);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    try {
      const [analytics, trendData] = await Promise.all([
        getIncidentAnalytics(),
        getMetricsTrends(),
      ]);
      setData(analytics);
      setTrends(trendData);
      setError(null);
    } catch {
      setError('Failed to load metrics');
    }
  }, []);

  useEffect(() => {
    load();
    const interval = window.setInterval(load, 15000);
    return () => window.clearInterval(interval);
  }, [load]);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="loading-text">Loading metrics…</p>;

  const mttaData = trends?.trends?.map(d => ({ date: d.date, 'MTTA (min)': Math.round(d.mtta / 60 * 10) / 10 })) ?? [];
  const mttrData = trends?.trends?.map(d => ({ date: d.date, 'MTTR (min)': Math.round(d.mttr / 60 * 10) / 10 })) ?? [];
  const incidentVolume = trends?.trends?.map(d => ({ date: d.date, Incidents: d.incidents })) ?? [];

  return (
    <div className="page">
      {/* Summary Stats */}
      <IncidentAnalytics summary={data.summary} byService={data.by_service} />

      {/* MTTA Trend Chart */}
      <div className="chart-card">
        <h3>MTTA Trend (Mean Time to Acknowledge)</h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={mttaData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
            <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={false} unit=" min" />
            <Tooltip content={<CustomTooltip valueFormatter={(v) => `${v} min`} />} />
            <Line type="monotone" dataKey="MTTA (min)" stroke="#0891b2" strokeWidth={2.5} dot={{ fill: '#0891b2', r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* MTTR Trend Chart */}
      <div className="chart-card">
        <h3>MTTR Trend (Mean Time to Resolve)</h3>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={mttrData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
            <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={false} unit=" min" />
            <Tooltip content={<CustomTooltip valueFormatter={(v) => `${v} min`} />} />
            <Line type="monotone" dataKey="MTTR (min)" stroke="#ca8a04" strokeWidth={2.5} dot={{ fill: '#ca8a04', r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Incident Volume */}
      <div className="chart-card">
        <h3>Daily Incident Volume</h3>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={incidentVolume}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
            <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} />
            <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={false} allowDecimals={false} />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="Incidents" fill="#111827" radius={[4, 4, 0, 0]} barSize={28} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Per-Service MTTA/MTTR Trend */}
      {trends?.by_service?.length > 0 && (
        <div className="chart-card">
          <h3>MTTA by Service (14-day trend)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={{ stroke: '#e5e7eb' }} type="category" allowDuplicatedCategory={false} />
              <YAxis tick={{ fontSize: 12, fill: '#9ca3af' }} tickLine={false} axisLine={false} unit=" min" />
              <Tooltip content={<CustomTooltip valueFormatter={(v) => `${v} min`} />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {trends.by_service.map((svc, idx) => (
                <Line
                  key={svc.service}
                  data={svc.data.map(d => ({ date: d.date, [svc.service]: Math.round(d.mtta / 60 * 10) / 10 }))}
                  dataKey={svc.service}
                  name={svc.service}
                  type="monotone"
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export default Metrics;
