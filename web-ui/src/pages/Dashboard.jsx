import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
	ArrowRight,
	RefreshCw,
	ExternalLink,
	CheckCircle2,
	Circle,
} from 'lucide-react';
import { listIncidents, getIncidentAnalytics, getCurrentOncall, updateIncident, checkAllServices } from '../services/api';
import { severityColor, statusColor, timeAgo, formatSeconds } from '../utils/formatters';
import { cn } from '../lib/utils';

function SeverityDot({ severity }) {
	const colors = {
		critical: 'bg-red-500',
		high: 'bg-orange-500',
		medium: 'bg-amber-400',
		low: 'bg-blue-400',
	};
	return (
		<span className={cn('inline-block h-2 w-2 rounded-full', colors[severity] || 'bg-gray-300')}
			title={severity} />
	);
}

export default function Dashboard() {
	const [incidents, setIncidents] = useState([]);
	const [analytics, setAnalytics] = useState(null);
	const [oncall, setOncall] = useState(null);
	const [serviceStatus, setServiceStatus] = useState([]);
	const [loading, setLoading] = useState(true);
	const [hoveredRow, setHoveredRow] = useState(null);

	const fetchData = useCallback(async () => {
		try {
			const [incRes, analyticsRes, oncallRes, healthRes] = await Promise.allSettled([
				listIncidents({ limit: 25 }),
				getIncidentAnalytics(),
				getCurrentOncall(),
				checkAllServices(),
			]);
			if (incRes.status === 'fulfilled') setIncidents(incRes.value.incidents || []);
			if (analyticsRes.status === 'fulfilled') setAnalytics(analyticsRes.value);
			if (oncallRes.status === 'fulfilled') setOncall(oncallRes.value);
			if (healthRes.status === 'fulfilled') setServiceStatus(healthRes.value);
		} finally {
			setLoading(false);
		}
	}, []);

	useEffect(() => {
		fetchData();
		const interval = setInterval(fetchData, 30000);
		return () => clearInterval(interval);
	}, [fetchData]);

	const handleAcknowledge = async (e, incidentId) => {
		e.preventDefault();
		e.stopPropagation();
		try {
			await updateIncident(incidentId, { status: 'acknowledged' });
			fetchData();
		} catch (err) {
			console.error('Failed to acknowledge:', err);
		}
	};

	const openCount = analytics?.open_count ?? incidents.filter((i) => i.status === 'open').length;
	const upCount = serviceStatus.filter((s) => s.status === 'up').length;
	const allUp = serviceStatus.length > 0 && serviceStatus.every((s) => s.status === 'up');
	const primaryOncall = oncall?.primary?.name || oncall?.primary?.email || null;

	if (loading) {
		return (
			<div className="flex h-[60vh] items-center justify-center">
				<RefreshCw className="h-5 w-5 animate-spin text-zinc-300" />
			</div>
		);
	}

	return (
		<div className="fade-in space-y-6">
			{/* Page header */}
			<div className="flex items-end justify-between">
				<h1 className="text-xl font-semibold text-zinc-900">Overview</h1>
				<button
					onClick={fetchData}
					className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
				>
					<RefreshCw className="h-3 w-3" />
					Refresh
				</button>
			</div>

			{/* Status banner */}
			<div className={cn(
				'flex items-center justify-between rounded-lg px-4 py-3',
				allUp
					? 'bg-emerald-50 border border-emerald-200/60'
					: 'bg-red-50 border border-red-200/60'
			)}>
				<div className="flex items-center gap-2.5">
					<span className={cn(
						'h-2 w-2 rounded-full',
						allUp ? 'bg-emerald-500' : 'bg-red-500'
					)} />
					<span className={cn(
						'text-sm font-medium',
						allUp ? 'text-emerald-800' : 'text-red-800'
					)}>
						{allUp ? 'All systems operational' : 'Service degradation detected'}
					</span>
				</div>
				<span className="text-xs text-zinc-500">
					{upCount}/{serviceStatus.length} services healthy
				</span>
			</div>

			{/* Inline metrics strip */}
			<div className="flex items-center gap-8 text-sm">
				<div>
					<span className="text-zinc-500">Open incidents</span>
					<span className={cn('ml-2 font-semibold tabular-nums', openCount > 0 ? 'text-red-600' : 'text-zinc-900')}>
						{openCount}
					</span>
				</div>
				<div className="h-4 w-px bg-zinc-200" />
				<div>
					<span className="text-zinc-500">MTTR avg</span>
					<span className="ml-2 font-semibold text-zinc-900 tabular-nums">
						{formatSeconds(analytics?.avg_mttr_seconds)}
					</span>
				</div>
				<div className="h-4 w-px bg-zinc-200" />
				<div>
					<span className="text-zinc-500">On-call</span>
					<span className="ml-2 font-medium text-zinc-900">
						{primaryOncall || 'None'}
					</span>
				</div>
				<div className="h-4 w-px bg-zinc-200" />
				<div>
					<span className="text-zinc-500">Total tracked</span>
					<span className="ml-2 font-semibold text-zinc-900 tabular-nums">{incidents.length}</span>
				</div>
			</div>

			{/* Incidents table */}
			<div>
				<div className="flex items-center justify-between mb-3">
					<h2 className="text-sm font-medium text-zinc-900">Recent incidents</h2>
					<Link
						to="/incidents"
						className="flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
					>
						View all <ArrowRight className="h-3 w-3" />
					</Link>
				</div>

				<div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
					<table className="w-full text-sm">
						<thead>
							<tr className="border-b border-zinc-100 bg-zinc-50/50">
								<th className="py-2 pl-4 pr-2 text-left text-xs font-medium text-zinc-500 w-8"></th>
								<th className="py-2 px-3 text-left text-xs font-medium text-zinc-500">Incident</th>
								<th className="py-2 px-3 text-left text-xs font-medium text-zinc-500">Service</th>
								<th className="py-2 px-3 text-left text-xs font-medium text-zinc-500">Status</th>
								<th className="py-2 px-3 text-left text-xs font-medium text-zinc-500">Opened</th>
								<th className="py-2 px-3 text-left text-xs font-medium text-zinc-500">Assignee</th>
								<th className="py-2 px-3 w-24"></th>
							</tr>
						</thead>
						<tbody>
							{incidents.length === 0 ? (
								<tr>
									<td colSpan={7} className="py-16 text-center">
										<CheckCircle2 className="mx-auto h-6 w-6 text-emerald-300 mb-2" />
										<p className="text-sm text-zinc-400">No active incidents</p>
									</td>
								</tr>
							) : (
								incidents.map((inc) => (
									<tr
										key={inc.incident_id}
										className="group border-b last:border-0 border-zinc-50 hover:bg-zinc-50/60 transition-colors"
										onMouseEnter={() => setHoveredRow(inc.incident_id)}
										onMouseLeave={() => setHoveredRow(null)}
									>
										<td className="py-2.5 pl-4 pr-2">
											<SeverityDot severity={inc.severity} />
										</td>
										<td className="py-2.5 px-3">
											<Link
												to={`/incidents/${inc.incident_id}`}
												className="hover:text-blue-600 transition-colors"
											>
												<span className="font-mono text-[11px] text-zinc-400 mr-1.5">
													{inc.incident_id.slice(0, 8)}
												</span>
												<span className="font-medium text-zinc-800 truncate">
													{inc.title}
												</span>
											</Link>
										</td>
										<td className="py-2.5 px-3">
											<span className="text-xs text-zinc-500">{inc.service}</span>
										</td>
										<td className="py-2.5 px-3">
											<span className={cn(
												'inline-flex items-center gap-1 text-xs font-medium capitalize',
												inc.status === 'open' ? 'text-red-600' :
													inc.status === 'acknowledged' ? 'text-amber-600' :
														inc.status === 'resolved' ? 'text-emerald-600' :
															'text-zinc-500'
											)}>
												<Circle className="h-1.5 w-1.5 fill-current" />
												{inc.status}
											</span>
										</td>
										<td className="py-2.5 px-3 text-xs text-zinc-400 tabular-nums">
											{timeAgo(inc.created_at)}
										</td>
										<td className="py-2.5 px-3 text-xs text-zinc-500">
											{inc.assigned_to || <span className="text-zinc-300">—</span>}
										</td>
										<td className="py-2.5 px-3 text-right">
											{hoveredRow === inc.incident_id && inc.status === 'open' ? (
												<button
													onClick={(e) => handleAcknowledge(e, inc.incident_id)}
													className="text-[11px] font-medium text-amber-600 hover:text-amber-700 transition-colors"
												>
													Ack
												</button>
											) : (
												<Link
													to={`/incidents/${inc.incident_id}`}
													className="text-zinc-300 opacity-0 group-hover:opacity-100 transition-opacity"
												>
													<ExternalLink className="h-3.5 w-3.5" />
												</Link>
											)}
										</td>
									</tr>
								))
							)}
						</tbody>
					</table>
				</div>
			</div>
		</div>
	);
}
