import { useEffect, useCallback, useState } from 'react';
import IncidentList from '../components/IncidentList.jsx';
import IncidentAnalytics from '../components/IncidentAnalytics.jsx';
import { useIncidentSocket } from '../hooks/useIncidentSocket.js';
import { getIncidentAnalytics, listIncidents, getMetricsTrends } from '../services/api.js';

function Dashboard() {
	const [incidents, setIncidents] = useState([]);
	const [total, setTotal] = useState(0);
	const [analytics, setAnalytics] = useState(null);
	const [trends, setTrends] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);

	const loadIncidents = useCallback(async () => {
		try {
			const data = await listIncidents({ limit: 50 });
			setIncidents(data.incidents ?? []);
			setTotal(data.total ?? data.incidents?.length ?? 0);
			setError(null);
		} catch {
			setError('Failed to load incidents');
		}
	}, []);

	const loadAnalytics = useCallback(async () => {
		try {
			const [data, trendData] = await Promise.all([
				getIncidentAnalytics(),
				getMetricsTrends(),
			]);
			setAnalytics(data);
			setTrends(trendData);
		} catch {
			setError('Failed to load analytics');
		}
	}, []);

	const loadAll = useCallback(async () => {
		setLoading(true);
		await Promise.all([loadIncidents(), loadAnalytics()]);
		setLoading(false);
	}, [loadIncidents, loadAnalytics]);

	useEffect(() => {
		loadAll();
		const id = window.setInterval(loadAll, Number(import.meta.env.VITE_POLL_INTERVAL || 30000));
		return () => window.clearInterval(id);
	}, [loadAll]);

	useIncidentSocket(loadAll);

	const mttaTrend = trends?.trends?.map(d => d.mtta) ?? [];
	const mttrTrend = trends?.trends?.map(d => d.mttr) ?? [];

	return (
		<div className="page">
			{error && <div className="error-banner">{error}</div>}

			{/* Metrics status bar */}
			{analytics && (
				<IncidentAnalytics
					summary={analytics.summary}
					byService={analytics.by_service}
					mttaTrend={mttaTrend}
					mttrTrend={mttrTrend}
				/>
			)}

			{/* Incidents table */}
			<IncidentList incidents={incidents} total={total} />

			{loading && <span className="loading-text">Refreshing…</span>}
		</div>
	);
}

export default Dashboard;
