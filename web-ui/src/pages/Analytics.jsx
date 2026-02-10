import { useQuery } from '@tanstack/react-query';
import {
	BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
	Tooltip as RechartsTooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import { BarChart3, TrendingDown, Clock, Timer, AlertTriangle, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getIncidentAnalytics, getCorrelationStats, listIncidents } from '@/services/api';
import { formatSeconds, severityColor } from '@/utils/formatters';
import { cn } from '@/lib/utils';

const CHART_COLORS = {
	primary: '#6366f1',
	emerald: '#10b981',
	amber: '#f59e0b',
	red: '#ef4444',
	blue: '#3b82f6',
	purple: '#a855f7',
	zinc: '#71717a',
};

const SEVERITY_COLORS = { critical: '#ef4444', high: '#f97316', medium: '#eab308', low: '#3b82f6', info: '#06b6d4' };
const STATUS_COLORS = { open: '#ef4444', acknowledged: '#eab308', investigating: '#a855f7', mitigated: '#3b82f6', resolved: '#10b981', closed: '#71717a' };

const CustomTooltip = ({ active, payload, label }) => {
	if (!active || !payload?.length) return null;
	return (
		<div className="rounded-lg border border-border bg-card px-3 py-2 shadow-lg">
			<p className="text-xs font-medium mb-1">{label}</p>
			{payload.map((p, i) => (
				<p key={i} className="text-xs" style={{ color: p.color }}>{p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}</p>
			))}
		</div>
	);
};

export default function Analytics() {
	const { data: analytics, isLoading: analyticsLoading } = useQuery({
		queryKey: ['analytics'],
		queryFn: getIncidentAnalytics,
		refetchInterval: 30000,
	});
	const { data: correlationStats } = useQuery({
		queryKey: ['correlation-stats'],
		queryFn: getCorrelationStats,
		refetchInterval: 30000,
	});
	const { data: incidents = [] } = useQuery({
		queryKey: ['all-incidents'],
		queryFn: () => listIncidents({ limit: 200 }),
		refetchInterval: 30000,
	});

	const incidentList = Array.isArray(incidents) ? incidents : incidents?.incidents || [];

	// Severity distribution
	const severityDist = Object.entries(
		incidentList.reduce((acc, i) => { acc[i.severity] = (acc[i.severity] || 0) + 1; return acc; }, {})
	).map(([name, value]) => ({ name, value }));

	// Status distribution
	const statusDist = Object.entries(
		incidentList.reduce((acc, i) => { acc[i.status] = (acc[i.status] || 0) + 1; return acc; }, {})
	).map(([name, value]) => ({ name, value }));

	// Service breakdown
	const serviceDist = Object.entries(
		incidentList.reduce((acc, i) => { const s = i.service || 'unknown'; acc[s] = (acc[s] || 0) + 1; return acc; }, {})
	).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value).slice(0, 10);

	const mtta = analytics?.avg_mtta_seconds;
	const mttr = analytics?.avg_mttr_seconds;
	const totalIncidents = analytics?.total_incidents || incidentList.length;
	const noiseReduction = correlationStats?.noise_reduction_percentage || correlationStats?.dedup_ratio;

	return (
		<div className="space-y-6 fade-in">
			<div>
				<h1 className="text-2xl font-bold tracking-tight">Analytics</h1>
				<p className="text-sm text-muted-foreground mt-1">Incident trends, response times, and alert correlation insights</p>
			</div>

			{/* KPI Cards */}
			<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
				<Card>
					<CardContent className="p-5">
						<div className="flex items-center gap-3">
							<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10"><Timer className="h-5 w-5 text-blue-400" /></div>
							<div><p className="text-[11px] text-muted-foreground uppercase tracking-wide">MTTA</p><p className="text-xl font-bold">{formatSeconds(mtta)}</p></div>
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-5">
						<div className="flex items-center gap-3">
							<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10"><Clock className="h-5 w-5 text-purple-400" /></div>
							<div><p className="text-[11px] text-muted-foreground uppercase tracking-wide">MTTR</p><p className="text-xl font-bold">{formatSeconds(mttr)}</p></div>
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-5">
						<div className="flex items-center gap-3">
							<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-500/10"><AlertTriangle className="h-5 w-5 text-red-400" /></div>
							<div><p className="text-[11px] text-muted-foreground uppercase tracking-wide">Total Incidents</p><p className="text-xl font-bold">{totalIncidents}</p></div>
						</div>
					</CardContent>
				</Card>
				<Card>
					<CardContent className="p-5">
						<div className="flex items-center gap-3">
							<div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10"><TrendingDown className="h-5 w-5 text-emerald-400" /></div>
							<div><p className="text-[11px] text-muted-foreground uppercase tracking-wide">Noise Reduction</p><p className="text-xl font-bold">{noiseReduction != null ? `${Math.round(noiseReduction)}%` : '—'}</p></div>
						</div>
					</CardContent>
				</Card>
			</div>

			{/* Charts Grid */}
			<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
				{/* Severity Distribution */}
				<Card>
					<CardHeader className="pb-2"><CardTitle className="text-sm">Severity Distribution</CardTitle></CardHeader>
					<CardContent>
						{severityDist.length > 0 ? (
							<ResponsiveContainer width="100%" height={260}>
								<PieChart>
									<Pie data={severityDist} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value" nameKey="name">
										{severityDist.map((e, i) => <Cell key={i} fill={SEVERITY_COLORS[e.name] || CHART_COLORS.zinc} stroke="transparent" />)}
									</Pie>
									<RechartsTooltip content={<CustomTooltip />} />
									<Legend wrapperStyle={{ fontSize: '11px', color: '#71717a' }} />
								</PieChart>
							</ResponsiveContainer>
						) : <p className="text-sm text-muted-foreground text-center py-12">No data</p>}
					</CardContent>
				</Card>

				{/* Status Distribution */}
				<Card>
					<CardHeader className="pb-2"><CardTitle className="text-sm">Status Distribution</CardTitle></CardHeader>
					<CardContent>
						{statusDist.length > 0 ? (
							<ResponsiveContainer width="100%" height={260}>
								<PieChart>
									<Pie data={statusDist} cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3} dataKey="value" nameKey="name">
										{statusDist.map((e, i) => <Cell key={i} fill={STATUS_COLORS[e.name] || CHART_COLORS.zinc} stroke="transparent" />)}
									</Pie>
									<RechartsTooltip content={<CustomTooltip />} />
									<Legend wrapperStyle={{ fontSize: '11px', color: '#71717a' }} />
								</PieChart>
							</ResponsiveContainer>
						) : <p className="text-sm text-muted-foreground text-center py-12">No data</p>}
					</CardContent>
				</Card>

				{/* Top Services */}
				<Card className="lg:col-span-2">
					<CardHeader className="pb-2"><CardTitle className="text-sm">Incidents by Service</CardTitle></CardHeader>
					<CardContent>
						{serviceDist.length > 0 ? (
							<ResponsiveContainer width="100%" height={300}>
								<BarChart data={serviceDist} layout="vertical" margin={{ left: 0, right: 20 }}>
									<CartesianGrid strokeDasharray="3 3" stroke="#27272a" horizontal={false} />
									<XAxis type="number" tick={{ fill: '#71717a', fontSize: 11 }} axisLine={{ stroke: '#27272a' }} />
									<YAxis type="category" dataKey="name" width={140} tick={{ fill: '#a1a1aa', fontSize: 11 }} axisLine={false} tickLine={false} />
									<RechartsTooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(99,102,241,0.08)' }} />
									<Bar dataKey="value" name="Incidents" fill={CHART_COLORS.primary} radius={[0, 4, 4, 0]} barSize={20} />
								</BarChart>
							</ResponsiveContainer>
						) : <p className="text-sm text-muted-foreground text-center py-12">No data</p>}
					</CardContent>
				</Card>
			</div>

			{/* Correlation Stats */}
			{correlationStats && (
				<Card>
					<CardHeader className="pb-3">
						<div className="flex items-center gap-2">
							<Zap className="h-4 w-4 text-yellow-400" />
							<CardTitle className="text-sm">Alert Correlation Statistics</CardTitle>
						</div>
					</CardHeader>
					<CardContent>
						<div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
							{Object.entries(correlationStats).filter(([k]) => !k.startsWith('_')).map(([key, val]) => (
								<div key={key} className="rounded-lg border border-border p-3 text-center">
									<p className="text-lg font-bold">{typeof val === 'number' ? (val % 1 !== 0 ? val.toFixed(1) : val) : val}</p>
									<p className="text-[10px] text-muted-foreground uppercase tracking-wide mt-1">{key.replace(/_/g, ' ')}</p>
								</div>
							))}
						</div>
					</CardContent>
				</Card>
			)}
		</div>
	);
}
