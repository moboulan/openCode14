import { useEffect, useCallback, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useIncidentSocket } from '@/hooks/useIncidentSocket';
import { getIncidentAnalytics, listIncidents, getMetricsTrends } from '@/services/api';
import { formatDateTime, formatDuration, formatRelativeTime } from '@/utils/formatters';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
	AlertTriangle, Clock, CheckCircle2, Timer, TrendingUp,
	ArrowUpDown, ChevronDown, ChevronUp,
} from 'lucide-react';

const STATUSES = ['all', 'open', 'acknowledged', 'resolved'];
const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low'];

function Sparkline({ data = [], color = 'currentColor', width = 48, height = 16 }) {
	if (!data.length) return null;
	const max = Math.max(...data, 1);
	const min = Math.min(...data, 0);
	const range = max - min || 1;
	const step = width / Math.max(data.length - 1, 1);
	const points = data
		.map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - min) / range) * (height - 2) - 1).toFixed(1)}`)
		.join(' ');

	return (
		<svg width={width} height={height} className="inline-block">
			<polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
		</svg>
	);
}

function StatsCards({ summary, mttaTrend, mttrTrend }) {
	if (!summary) return null;

	const stats = [
		{ label: 'Total', value: summary.total ?? 0, icon: AlertTriangle, color: 'text-foreground' },
		{ label: 'Open', value: summary.open_count ?? 0, icon: AlertTriangle, color: 'text-status-open' },
		{ label: 'Acknowledged', value: summary.ack_count ?? 0, icon: Clock, color: 'text-status-acknowledged' },
		{ label: 'Resolved', value: summary.resolved_count ?? 0, icon: CheckCircle2, color: 'text-status-resolved' },
		{ label: 'Avg MTTA', value: formatDuration(summary.avg_mtta), icon: Timer, color: 'text-cyan-500', spark: mttaTrend, sparkColor: '#06b6d4' },
		{ label: 'Avg MTTR', value: formatDuration(summary.avg_mttr), icon: TrendingUp, color: 'text-yellow-500', spark: mttrTrend, sparkColor: '#eab308' },
	];

	return (
		<div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
			{stats.map((s) => (
				<Card key={s.label}>
					<CardContent className="flex items-center justify-between p-4">
						<div>
							<p className="text-xs text-muted-foreground">{s.label}</p>
							<p className={`text-xl font-bold font-mono ${s.color}`}>{s.value}</p>
						</div>
						<div className="flex flex-col items-end gap-1">
							<s.icon className={`h-4 w-4 ${s.color}`} />
							{s.spark?.length > 1 && <Sparkline data={s.spark} color={s.sparkColor} />}
						</div>
					</CardContent>
				</Card>
			))}
		</div>
	);
}

function IncidentTable({ incidents, total }) {
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
		if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
		else { setSortKey(key); setSortDir('desc'); }
	};

	const SortIcon = ({ col }) => {
		if (sortKey !== col) return <ArrowUpDown className="ml-1 inline h-3 w-3 opacity-30" />;
		return sortDir === 'asc'
			? <ChevronUp className="ml-1 inline h-3 w-3" />
			: <ChevronDown className="ml-1 inline h-3 w-3" />;
	};

	return (
		<Card>
			<CardHeader className="pb-3">
				<div className="flex flex-wrap items-center justify-between gap-3">
					<CardTitle className="text-base">Incidents</CardTitle>
					<span className="text-xs font-mono text-muted-foreground">
						{filtered.length}/{total ?? incidents.length}
					</span>
				</div>
				<div className="flex flex-wrap items-center gap-4 pt-2">
					{/* Status filter */}
					<div className="flex items-center gap-1.5">
						<span className="text-xs text-muted-foreground">Status</span>
						{STATUSES.map(s => (
							<Button
								key={s}
								variant={statusFilter === s ? 'default' : 'ghost'}
								size="sm"
								className="h-7 px-2 text-xs capitalize"
								onClick={() => setStatusFilter(s)}
							>
								{s}
							</Button>
						))}
					</div>
					<div className="h-4 w-px bg-border" />
					{/* Severity filter */}
					<div className="flex items-center gap-1.5">
						<span className="text-xs text-muted-foreground">Severity</span>
						{SEVERITIES.map(s => (
							<Button
								key={s}
								variant={severityFilter === s ? 'default' : 'ghost'}
								size="sm"
								className="h-7 px-2 text-xs capitalize"
								onClick={() => setSeverityFilter(s)}
							>
								{s}
							</Button>
						))}
					</div>
				</div>
			</CardHeader>
			<CardContent className="p-0">
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead className="cursor-pointer select-none" onClick={() => handleSort('title')}>
								Title <SortIcon col="title" />
							</TableHead>
							<TableHead className="cursor-pointer select-none" onClick={() => handleSort('service')}>
								Service <SortIcon col="service" />
							</TableHead>
							<TableHead className="cursor-pointer select-none" onClick={() => handleSort('severity')}>
								Severity <SortIcon col="severity" />
							</TableHead>
							<TableHead>Status</TableHead>
							<TableHead>Assigned</TableHead>
							<TableHead className="cursor-pointer select-none" onClick={() => handleSort('created_at')}>
								Created <SortIcon col="created_at" />
							</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{filtered.map((inc) => (
							<TableRow key={inc.incident_id} className="cursor-pointer">
								<TableCell>
									<Link to={`/incidents/${inc.incident_id}`} className="font-medium hover:underline">
										{inc.title}
									</Link>
								</TableCell>
								<TableCell><code className="text-xs">{inc.service}</code></TableCell>
								<TableCell><Badge variant={inc.severity}>{inc.severity}</Badge></TableCell>
								<TableCell><Badge variant={inc.status}>{inc.status}</Badge></TableCell>
								<TableCell className="text-muted-foreground text-xs">{inc.assigned_to || '—'}</TableCell>
								<TableCell className="text-xs font-mono text-muted-foreground whitespace-nowrap">
									{formatRelativeTime(inc.created_at)}
								</TableCell>
							</TableRow>
						))}
						{filtered.length === 0 && (
							<TableRow>
								<TableCell colSpan={6} className="text-center py-8 text-muted-foreground">
									No incidents match the current filters.
								</TableCell>
							</TableRow>
						)}
					</TableBody>
				</Table>
			</CardContent>
		</Card>
	);
}

export default function Dashboard() {
	const [incidents, setIncidents] = useState([]);
	const [total, setTotal] = useState(0);
	const [analytics, setAnalytics] = useState(null);
	const [trends, setTrends] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);

	const loadAll = useCallback(async () => {
		setLoading(true);
		try {
			const [incData, analyticsData, trendsData] = await Promise.allSettled([
				listIncidents({ limit: 50 }),
				getIncidentAnalytics(),
				getMetricsTrends(),
			]);
			if (incData.status === 'fulfilled') {
				setIncidents(incData.value.incidents ?? []);
				setTotal(incData.value.total ?? 0);
			}
			if (analyticsData.status === 'fulfilled') setAnalytics(analyticsData.value);
			if (trendsData.status === 'fulfilled') setTrends(trendsData.value);
			setError(null);
		} catch {
			setError('Failed to load data');
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		loadAll();
		const id = setInterval(loadAll, Number(import.meta.env.VITE_POLL_INTERVAL || 30000));
		return () => clearInterval(id);
	}, [loadAll]);

	useIncidentSocket(loadAll);

	const mttaTrend = trends?.trends?.map(d => d.mtta) ?? [];
	const mttrTrend = trends?.trends?.map(d => d.mttr) ?? [];

	return (
		<div className="space-y-6">
			{error && (
				<div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
					{error}
				</div>
			)}

			<StatsCards summary={analytics?.summary} mttaTrend={mttaTrend} mttrTrend={mttrTrend} />
			<IncidentTable incidents={incidents} total={total} />

			{loading && (
				<p className="text-xs text-muted-foreground animate-pulse">Refreshing…</p>
			)}
		</div>
	);
}
