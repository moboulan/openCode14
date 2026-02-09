import { useEffect, useCallback, useState } from 'react';
import {
	LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
	BarChart, Bar,
} from 'recharts';
import IncidentAnalytics from '../components/IncidentAnalytics.jsx';
import { getIncidentAnalytics, getMetricsTrends } from '../services/api.js';

function ChartTooltip({ active, payload, label, valueFormatter }) {
	if (!active || !payload?.length) return null;
	return (
		<div className="chart-tooltip">
			<div className="chart-tooltip__label">{label}</div>
			{payload.map((entry, idx) => (
				<div key={idx} className="chart-tooltip__row">
					<span className="chart-tooltip__dot" style={{ background: entry.color }} />
					<span>{entry.name}:</span>
					<span className="chart-tooltip__val">
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
		const interval = window.setInterval(load, Number(import.meta.env.VITE_METRICS_POLL_INTERVAL || 15000));
		return () => window.clearInterval(interval);
	}, [load]);

	if (error) return <div className="error-banner">{error}</div>;
	if (!data) return <p className="loading-text">Loading metrics…</p>;

	const mttaData = trends?.trends?.map(d => ({ date: d.date, 'MTTA (min)': Math.round(d.mtta / 60 * 10) / 10 })) ?? [];
	const mttrData = trends?.trends?.map(d => ({ date: d.date, 'MTTR (min)': Math.round(d.mttr / 60 * 10) / 10 })) ?? [];
	const incidentVolume = trends?.trends?.map(d => ({ date: d.date, Incidents: d.incidents })) ?? [];

	// Merge MTTA + MTTR into one dataset for the combined chart
	const combinedData = mttaData.map((d, i) => ({
		date: d.date,
		'MTTA (min)': d['MTTA (min)'],
		'MTTR (min)': mttrData[i]?.['MTTR (min)'] ?? 0,
	}));

	const mttaTrend = trends?.trends?.map(d => d.mtta) ?? [];
	const mttrTrend = trends?.trends?.map(d => d.mttr) ?? [];

	// Chart axis/grid colors that work in both themes via CSS vars
	const gridStroke = 'var(--border)';
	const tickFill = 'var(--text-muted)';

	return (
		<div className="page">
			{/* Summary status bar */}
			<IncidentAnalytics
				summary={data.summary}
				byService={data.by_service}
				mttaTrend={mttaTrend}
				mttrTrend={mttrTrend}
			/>

			{/* Split-pane: MTTA/MTTR line chart + Incident Volume bar chart */}
			<div className="split-pane">
				<div className="chart-card">
					<h3>MTTA / MTTR Trend</h3>
					<ResponsiveContainer width="100%" height={220}>
						<LineChart data={combinedData} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
							<CartesianGrid strokeDasharray="2 4" stroke={gridStroke} />
							<XAxis dataKey="date" tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} />
							<YAxis tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} unit=" min" />
							<Tooltip content={<ChartTooltip valueFormatter={(v) => `${v} min`} />} />
							<Line type="monotone" dataKey="MTTA (min)" stroke="var(--cyan)" strokeWidth={1.5} dot={false} />
							<Line type="monotone" dataKey="MTTR (min)" stroke="var(--yellow)" strokeWidth={1.5} dot={false} />
						</LineChart>
					</ResponsiveContainer>
				</div>

				<div className="chart-card">
					<h3>Daily Incident Volume</h3>
					<ResponsiveContainer width="100%" height={220}>
						<BarChart data={incidentVolume} margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
							<CartesianGrid strokeDasharray="2 4" stroke={gridStroke} vertical={false} />
							<XAxis dataKey="date" tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} />
							<YAxis tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} allowDecimals={false} />
							<Tooltip content={<ChartTooltip />} />
							<Bar dataKey="Incidents" fill="var(--accent)" radius={[2, 2, 0, 0]} barSize={18} />
						</BarChart>
					</ResponsiveContainer>
				</div>
			</div>

			{/* Per-Service MTTA/MTTR line chart */}
			{trends?.by_service?.length > 0 && (
				<div className="chart-card">
					<h3>MTTA by Service (14-day)</h3>
					<ResponsiveContainer width="100%" height={200}>
						<LineChart margin={{ top: 4, right: 8, bottom: 0, left: -10 }}>
							<CartesianGrid strokeDasharray="2 4" stroke={gridStroke} />
							<XAxis dataKey="date" tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} type="category" allowDuplicatedCategory={false} />
							<YAxis tick={{ fontSize: 10, fill: tickFill }} tickLine={false} axisLine={false} unit=" min" />
							<Tooltip content={<ChartTooltip valueFormatter={(v) => `${v} min`} />} />
							{trends.by_service.map((svc, idx) => {
								const colors = ['var(--red)', 'var(--orange)', 'var(--cyan)', 'var(--green)', 'var(--yellow)', 'var(--text-muted)'];
								return (
									<Line
										key={svc.service}
										data={svc.data.map(d => ({ date: d.date, [svc.service]: Math.round(d.mtta / 60 * 10) / 10 }))}
										dataKey={svc.service}
										name={svc.service}
										type="monotone"
										stroke={colors[idx % colors.length]}
										strokeWidth={1.5}
										dot={false}
									/>
								);
							})}
						</LineChart>
					</ResponsiveContainer>
				</div>
			)}
		</div>
	);
}

export default Metrics;
