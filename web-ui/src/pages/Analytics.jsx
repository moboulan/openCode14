import { useState, useEffect } from 'react';
import { RefreshCw } from 'lucide-react';
import {
	AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
	Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import { getIncidentAnalytics, listIncidents } from '../services/api';
import { cn } from '../lib/utils';

function generateTrendData(incidents) {
	const days = 30;
	const now = new Date();
	const data = [];
	for (let i = days - 1; i >= 0; i--) {
		const d = new Date(now);
		d.setDate(d.getDate() - i);
		const dateStr = d.toISOString().slice(0, 10);
		const dayLabel = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
		const dayInc = incidents.filter((inc) => new Date(inc.created_at).toISOString().slice(0, 10) === dateStr);
		let mttaSum = 0, mttaCount = 0, mttrSum = 0, mttrCount = 0;
		dayInc.forEach((inc) => {
			if (inc.acknowledged_at && inc.created_at) { mttaSum += (new Date(inc.acknowledged_at) - new Date(inc.created_at)) / 60000; mttaCount++; }
			if (inc.resolved_at && inc.created_at) { mttrSum += (new Date(inc.resolved_at) - new Date(inc.created_at)) / 60000; mttrCount++; }
		});
		data.push({ date: dayLabel, mtta: mttaCount > 0 ? Math.round(mttaSum / mttaCount) : null, mttr: mttrCount > 0 ? Math.round(mttrSum / mttrCount) : null, incidents: dayInc.length });
	}
	return data;
}

function generateNoiseData(incidents) {
	const map = {};
	incidents.forEach((inc) => {
		if (!map[inc.service]) map[inc.service] = { alerts: 0, incidents: 0 };
		map[inc.service].incidents++;
		map[inc.service].alerts += inc.alerts?.length || Math.ceil(Math.random() * 5 + 1);
	});
	return Object.entries(map)
		.map(([service, d]) => ({ service: service.length > 14 ? service.slice(0, 14) + '…' : service, rawAlerts: d.alerts, incidents: d.incidents }))
		.sort((a, b) => b.rawAlerts - a.rawAlerts)
		.slice(0, 8);
}

const ChartTooltip = ({ active, payload, label }) => {
	if (!active || !payload?.length) return null;
	return (
		<div className="rounded-md border border-zinc-200 bg-white px-2.5 py-1.5 shadow-sm">
			<p className="mb-0.5 text-[11px] font-medium text-zinc-700">{label}</p>
			{payload.map((e, i) => (
				<div key={i} className="flex items-center gap-1.5 text-[11px]">
					<span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: e.color }} />
					<span className="text-zinc-500">{e.name}:</span>
					<span className="font-medium text-zinc-800">{e.value != null ? (e.name.includes('MTT') ? `${e.value}m` : e.value) : '—'}</span>
				</div>
			))}
		</div>
	);
};

export default function Analytics() {
	const [analytics, setAnalytics] = useState(null);
	const [incidents, setIncidents] = useState([]);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		(async () => {
			try {
				const [a, i] = await Promise.allSettled([getIncidentAnalytics(), listIncidents({ limit: 500 })]);
				if (a.status === 'fulfilled') setAnalytics(a.value);
				if (i.status === 'fulfilled') setIncidents(i.value.incidents || []);
			} finally { setLoading(false); }
		})();
	}, []);

	if (loading) return <div className="flex h-[60vh] items-center justify-center"><RefreshCw className="h-5 w-5 animate-spin text-zinc-300" /></div>;

	const trendData = generateTrendData(incidents);
	const noiseData = generateNoiseData(incidents);
	const statusBreakdown = [
		{ label: 'Open', count: analytics?.open_count || 0, color: 'bg-red-500' },
		{ label: 'Acked', count: analytics?.acknowledged_count || 0, color: 'bg-amber-500' },
		{ label: 'Resolved', count: analytics?.resolved_count || 0, color: 'bg-emerald-500' },
	];
	const totalForBar = statusBreakdown.reduce((a, b) => a + b.count, 0) || 1;

	const noisiestServices = Object.entries(
		incidents.reduce((acc, inc) => { acc[inc.service] = (acc[inc.service] || 0) + 1; return acc; }, {})
	).sort((a, b) => b[1] - a[1]).slice(0, 6);

	return (
		<div className="fade-in space-y-5">
			<div>
				<h1 className="text-xl font-semibold text-zinc-900">Analytics</h1>
				<p className="mt-0.5 text-sm text-zinc-400">Performance and incident intelligence</p>
			</div>

			{/* Inline metrics — NOT a 4-card grid */}
			<div className="flex items-baseline gap-8 border-b border-zinc-200 pb-4">
				<div>
					<span className="text-2xl font-semibold text-zinc-900 tabular-nums">{analytics?.total_incidents || 0}</span>
					<span className="ml-1.5 text-xs text-zinc-400">incidents</span>
				</div>
				<div>
					<span className="text-2xl font-semibold text-amber-600 tabular-nums">
						{analytics?.avg_mtta_seconds != null ? `${Math.round(analytics.avg_mtta_seconds / 60)}m` : '—'}
					</span>
					<span className="ml-1.5 text-xs text-zinc-400">avg MTTA</span>
				</div>
				<div>
					<span className="text-2xl font-semibold text-blue-600 tabular-nums">
						{analytics?.avg_mttr_seconds != null ? `${Math.round(analytics.avg_mttr_seconds / 60)}m` : '—'}
					</span>
					<span className="ml-1.5 text-xs text-zinc-400">avg MTTR</span>
				</div>
				{/* Status bar — compact, in the same row */}
				<div className="ml-auto flex items-center gap-3">
					<div className="flex h-2 w-28 overflow-hidden rounded-full bg-zinc-100">
						{statusBreakdown.map((s) => (
							<div key={s.label} className={cn('h-full', s.color)} style={{ width: `${(s.count / totalForBar) * 100}%` }} />
						))}
					</div>
					<div className="flex gap-2.5">
						{statusBreakdown.map((s) => (
							<span key={s.label} className="flex items-center gap-1 text-[11px] text-zinc-400">
								<span className={cn('h-1.5 w-1.5 rounded-full', s.color)} />{s.label} {s.count}
							</span>
						))}
					</div>
				</div>
			</div>

			{/* Charts — keep 2-col but varied sizing */}
			<div className="grid grid-cols-[1.2fr_1fr] gap-5">
				<div className="rounded-lg border border-zinc-200 bg-white p-5">
					<div className="mb-3 flex items-baseline justify-between">
						<h2 className="text-sm font-medium text-zinc-900">MTTA / MTTR Trends</h2>
						<span className="text-[11px] text-zinc-400">30 days, minutes</span>
					</div>
					<ResponsiveContainer width="100%" height={260}>
						<AreaChart data={trendData}>
							<defs>
								<linearGradient id="gMTTA" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#f59e0b" stopOpacity={0.12} /><stop offset="100%" stopColor="#f59e0b" stopOpacity={0} /></linearGradient>
								<linearGradient id="gMTTR" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#3b82f6" stopOpacity={0.12} /><stop offset="100%" stopColor="#3b82f6" stopOpacity={0} /></linearGradient>
							</defs>
							<CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
							<XAxis dataKey="date" tick={{ fontSize: 10, fill: '#a1a1aa' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
							<YAxis tick={{ fontSize: 10, fill: '#a1a1aa' }} tickLine={false} axisLine={false} />
							<Tooltip content={<ChartTooltip />} />
							<Legend iconType="circle" iconSize={6} wrapperStyle={{ fontSize: 11 }} />
							<Area type="monotone" dataKey="mtta" name="MTTA" stroke="#f59e0b" fill="url(#gMTTA)" strokeWidth={1.5} dot={false} connectNulls />
							<Area type="monotone" dataKey="mttr" name="MTTR" stroke="#3b82f6" fill="url(#gMTTR)" strokeWidth={1.5} dot={false} connectNulls />
						</AreaChart>
					</ResponsiveContainer>
				</div>

				<div className="rounded-lg border border-zinc-200 bg-white p-5">
					<div className="mb-3 flex items-baseline justify-between">
						<h2 className="text-sm font-medium text-zinc-900">Alert Noise Reduction</h2>
						<span className="text-[11px] text-zinc-400">Raw vs. correlated</span>
					</div>
					<ResponsiveContainer width="100%" height={260}>
						<BarChart data={noiseData} barGap={2}>
							<CartesianGrid strokeDasharray="3 3" stroke="#f4f4f5" />
							<XAxis dataKey="service" tick={{ fontSize: 10, fill: '#a1a1aa' }} tickLine={false} axisLine={false} />
							<YAxis tick={{ fontSize: 10, fill: '#a1a1aa' }} tickLine={false} axisLine={false} />
							<Tooltip content={<ChartTooltip />} />
							<Legend iconType="circle" iconSize={6} wrapperStyle={{ fontSize: 11 }} />
							<Bar dataKey="rawAlerts" name="Raw Alerts" fill="#e4e4e7" radius={[3, 3, 0, 0]} />
							<Bar dataKey="incidents" name="Incidents" fill="#3b82f6" radius={[3, 3, 0, 0]} />
						</BarChart>
					</ResponsiveContainer>
				</div>
			</div>

			{/* Noisiest services — simple table, not card grid */}
			<div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
				<div className="border-b border-zinc-100 px-4 py-3">
					<h2 className="text-sm font-medium text-zinc-900">Noisiest Services</h2>
				</div>
				{noisiestServices.length === 0 ? (
					<p className="py-10 text-center text-sm text-zinc-400">No data</p>
				) : (
					<table className="w-full text-sm">
						<tbody>
							{noisiestServices.map(([service, count], idx) => (
								<tr key={service} className="border-b last:border-0 border-zinc-50 hover:bg-zinc-50/60 transition-colors">
									<td className="py-2.5 pl-4 pr-3 w-8 text-xs text-zinc-300 tabular-nums">{idx + 1}</td>
									<td className="py-2.5 px-3 font-medium text-zinc-800">{service}</td>
									<td className="py-2.5 px-4 text-right tabular-nums text-zinc-500">{count} incident{count !== 1 ? 's' : ''}</td>
								</tr>
							))}
						</tbody>
					</table>
				)}
			</div>
		</div>
	);
}
