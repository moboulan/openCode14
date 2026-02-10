import { useState, useEffect } from 'react';
import { CheckCircle2, XCircle, RefreshCw } from 'lucide-react';
import { checkAllServices, getIncidentAnalytics } from '../services/api';
import { cn } from '../lib/utils';

const serviceLabels = {
	'alert-ingestion': 'Alert Ingestion',
	'incident-management': 'Incident Management',
	'oncall-service': 'On-Call Service',
	'notification-service': 'Notification Service',
};

export default function SystemHealth() {
	const [services, setServices] = useState([]);
	const [analytics, setAnalytics] = useState(null);
	const [loading, setLoading] = useState(true);
	const [lastRefresh, setLastRefresh] = useState(null);

	const fetchData = async () => {
		setLoading(true);
		try {
			const [h, a] = await Promise.allSettled([checkAllServices(), getIncidentAnalytics()]);
			if (h.status === 'fulfilled') setServices(h.value);
			if (a.status === 'fulfilled') setAnalytics(a.value);
			setLastRefresh(new Date());
		} finally { setLoading(false); }
	};

	useEffect(() => { fetchData(); const i = setInterval(fetchData, 30000); return () => clearInterval(i); }, []);

	const allUp = services.length > 0 && services.every((s) => s.status === 'up');
	const upCount = services.filter((s) => s.status === 'up').length;
	const severityBreakdown = analytics?.by_severity || {};
	const serviceBreakdown = analytics?.by_service || {};

	return (
		<div className="fade-in space-y-5">
			<div className="flex items-end justify-between">
				<div>
					<h1 className="text-xl font-semibold text-zinc-900">Health</h1>
					<p className="mt-0.5 text-sm text-zinc-400">
						Infrastructure status
						{lastRefresh && <span className="ml-1">· {lastRefresh.toLocaleTimeString()}</span>}
					</p>
				</div>
				<button onClick={fetchData} className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-600 transition-colors">
					<RefreshCw className={cn('h-3 w-3', loading && 'animate-spin')} /> Refresh
				</button>
			</div>

			{/* Status banner — same pattern as Dashboard */}
			<div className={cn(
				'flex items-center gap-2.5 rounded-lg border px-4 py-3',
				allUp ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-red-200 bg-red-50 text-red-700'
			)}>
				{allUp ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
				<span className="text-sm font-medium">{allUp ? 'All systems operational' : 'Degradation detected'}</span>
				<span className="ml-auto text-xs opacity-70">{upCount}/{services.length} healthy</span>
			</div>

			{/* Services — table, not 4-column card grid */}
			<div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
				<table className="w-full text-sm">
					<thead>
						<tr className="border-b border-zinc-100 bg-zinc-50/50">
							<th className="py-2 pl-4 pr-3 text-left text-xs font-medium text-zinc-500">Service</th>
							<th className="py-2 px-3 text-left text-xs font-medium text-zinc-500">Endpoint</th>
							<th className="py-2 px-3 text-left text-xs font-medium text-zinc-500">Version</th>
							<th className="py-2 px-3 text-right text-xs font-medium text-zinc-500">Status</th>
						</tr>
					</thead>
					<tbody>
						{services.map((svc, idx) => {
							const isUp = svc.status === 'up';
							return (
								<tr key={svc.service} className="border-b last:border-0 border-zinc-50 hover:bg-zinc-50/60 transition-colors">
									<td className="py-2.5 pl-4 pr-3 font-medium text-zinc-800">{serviceLabels[svc.service] || svc.service}</td>
									<td className="py-2.5 px-3 font-mono text-xs text-zinc-400">{svc.service}:800{idx + 1}</td>
									<td className="py-2.5 px-3 text-xs text-zinc-400">{svc.version ? `v${svc.version}` : '—'}</td>
									<td className="py-2.5 px-3 text-right">
										<span className={cn('inline-flex items-center gap-1.5 text-xs font-medium', isUp ? 'text-emerald-600' : 'text-red-600')}>
											<span className={cn('h-1.5 w-1.5 rounded-full', isUp ? 'bg-emerald-500' : 'bg-red-500')} />
											{isUp ? 'Healthy' : 'Down'}
										</span>
									</td>
								</tr>
							);
						})}
					</tbody>
				</table>
			</div>

			{/* Breakdowns — 2-col with bars */}
			<div className="grid grid-cols-2 gap-5">
				<div className="rounded-lg border border-zinc-200 bg-white p-4">
					<h2 className="mb-3 text-sm font-medium text-zinc-900">By Severity</h2>
					<div className="space-y-2.5">
						{['critical', 'high', 'medium', 'low'].map((sev) => {
							const count = severityBreakdown[sev] || 0;
							const total = analytics?.total_incidents || 1;
							const pct = Math.round((count / total) * 100);
							const colors = { critical: 'bg-red-500', high: 'bg-orange-500', medium: 'bg-amber-400', low: 'bg-blue-400' };
							return (
								<div key={sev} className="flex items-center gap-3">
									<span className="w-14 text-xs capitalize text-zinc-500">{sev}</span>
									<div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
										<div className={cn('h-full rounded-full', colors[sev])} style={{ width: `${pct}%` }} />
									</div>
									<span className="w-6 text-right text-xs tabular-nums text-zinc-600">{count}</span>
								</div>
							);
						})}
					</div>
				</div>

				<div className="rounded-lg border border-zinc-200 bg-white p-4">
					<h2 className="mb-3 text-sm font-medium text-zinc-900">By Service</h2>
					<div className="space-y-2.5">
						{Object.entries(serviceBreakdown).sort((a, b) => b[1] - a[1]).map(([service, count]) => {
							const total = analytics?.total_incidents || 1;
							const pct = Math.round((count / total) * 100);
							return (
								<div key={service} className="flex items-center gap-3">
									<span className="w-28 truncate text-xs text-zinc-500">{service}</span>
									<div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100">
										<div className="h-full rounded-full bg-blue-500" style={{ width: `${pct}%` }} />
									</div>
									<span className="w-6 text-right text-xs tabular-nums text-zinc-600">{count}</span>
								</div>
							);
						})}
						{Object.keys(serviceBreakdown).length === 0 && (
							<p className="py-6 text-center text-xs text-zinc-400">No data</p>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
