import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, RefreshCw, ChevronDown, ExternalLink, Circle } from 'lucide-react';
import { listIncidents, updateIncident } from '../services/api';
import { timeAgo } from '../utils/formatters';
import { cn } from '../lib/utils';

const SEVERITY_OPTIONS = ['all', 'critical', 'high', 'medium', 'low'];
const STATUS_OPTIONS = ['all', 'open', 'acknowledged', 'investigating', 'mitigated', 'resolved', 'closed'];

const sevDotColor = {
	critical: 'bg-red-500',
	high: 'bg-orange-500',
	medium: 'bg-amber-400',
	low: 'bg-blue-400',
};

const statusTextColor = {
	open: 'text-red-600',
	acknowledged: 'text-amber-600',
	investigating: 'text-purple-600',
	mitigated: 'text-blue-600',
	resolved: 'text-emerald-600',
	closed: 'text-zinc-400',
};

export default function Incidents() {
	const [incidents, setIncidents] = useState([]);
	const [total, setTotal] = useState(0);
	const [loading, setLoading] = useState(true);
	const [search, setSearch] = useState('');
	const [severityFilter, setSeverityFilter] = useState('all');
	const [statusFilter, setStatusFilter] = useState('all');
	const [hoveredRow, setHoveredRow] = useState(null);

	const fetchData = useCallback(async () => {
		setLoading(true);
		try {
			const params = { limit: 100 };
			if (severityFilter !== 'all') params.severity = severityFilter;
			if (statusFilter !== 'all') params.status = statusFilter;
			const res = await listIncidents(params);
			setIncidents(res.incidents || []);
			setTotal(res.total || 0);
		} finally {
			setLoading(false);
		}
	}, [severityFilter, statusFilter]);

	useEffect(() => { fetchData(); }, [fetchData]);

	const handleAck = async (e, incidentId) => {
		e.preventDefault();
		try {
			await updateIncident(incidentId, { status: 'acknowledged' });
			fetchData();
		} catch (err) {
			console.error('Ack failed:', err);
		}
	};

	const filtered = incidents.filter((inc) => {
		if (!search) return true;
		const q = search.toLowerCase();
		return (
			inc.title?.toLowerCase().includes(q) ||
			inc.incident_id?.toLowerCase().includes(q) ||
			inc.service?.toLowerCase().includes(q)
		);
	});

	return (
		<div className="fade-in space-y-5">
			<div className="flex items-end justify-between">
				<div>
					<h1 className="text-xl font-semibold text-zinc-900">Incidents</h1>
					<p className="mt-0.5 text-sm text-zinc-400">{total} total</p>
				</div>
				<button
					onClick={fetchData}
					className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-zinc-600 transition-colors"
				>
					<RefreshCw className={cn('h-3 w-3', loading && 'animate-spin')} />
					Refresh
				</button>
			</div>

			{/* Filters */}
			<div className="flex items-center gap-3">
				<div className="relative flex-1 max-w-xs">
					<Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-400" />
					<input
						type="text"
						placeholder="Search..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="w-full rounded-md border border-zinc-200 bg-white py-1.5 pl-8 pr-3 text-sm text-zinc-700 placeholder-zinc-400 outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-200"
					/>
				</div>
				<div className="relative">
					<select
						value={severityFilter}
						onChange={(e) => setSeverityFilter(e.target.value)}
						className="appearance-none rounded-md border border-zinc-200 bg-white py-1.5 pl-2.5 pr-7 text-xs font-medium text-zinc-600 outline-none focus:border-zinc-400"
					>
						{SEVERITY_OPTIONS.map((s) => (
							<option key={s} value={s}>{s === 'all' ? 'All severities' : s}</option>
						))}
					</select>
					<ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 text-zinc-400" />
				</div>
				<div className="relative">
					<select
						value={statusFilter}
						onChange={(e) => setStatusFilter(e.target.value)}
						className="appearance-none rounded-md border border-zinc-200 bg-white py-1.5 pl-2.5 pr-7 text-xs font-medium text-zinc-600 outline-none focus:border-zinc-400"
					>
						{STATUS_OPTIONS.map((s) => (
							<option key={s} value={s}>{s === 'all' ? 'All statuses' : s}</option>
						))}
					</select>
					<ChevronDown className="pointer-events-none absolute right-1.5 top-1/2 h-3 w-3 -translate-y-1/2 text-zinc-400" />
				</div>
			</div>

			{/* Table */}
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
							<th className="py-2 px-3 w-20"></th>
						</tr>
					</thead>
					<tbody>
						{loading && filtered.length === 0 ? (
							<tr>
								<td colSpan={7} className="py-16 text-center">
									<RefreshCw className="mx-auto h-5 w-5 animate-spin text-zinc-300" />
								</td>
							</tr>
						) : filtered.length === 0 ? (
							<tr>
								<td colSpan={7} className="py-16 text-center text-sm text-zinc-400">
									No incidents match your filters
								</td>
							</tr>
						) : (
							filtered.map((inc) => (
								<tr
									key={inc.incident_id}
									className="group border-b last:border-0 border-zinc-50 hover:bg-zinc-50/60 transition-colors"
									onMouseEnter={() => setHoveredRow(inc.incident_id)}
									onMouseLeave={() => setHoveredRow(null)}
								>
									<td className="py-2.5 pl-4 pr-2">
										<span className={cn('inline-block h-2 w-2 rounded-full', sevDotColor[inc.severity] || 'bg-zinc-300')} />
									</td>
									<td className="py-2.5 px-3">
										<Link to={`/incidents/${inc.incident_id}`} className="hover:text-blue-600 transition-colors">
											<span className="font-mono text-[11px] text-zinc-400 mr-1.5">{inc.incident_id.slice(0, 8)}</span>
											<span className="font-medium text-zinc-800">{inc.title}</span>
										</Link>
									</td>
									<td className="py-2.5 px-3 text-xs text-zinc-500">{inc.service}</td>
									<td className="py-2.5 px-3">
										<span className={cn('inline-flex items-center gap-1 text-xs font-medium capitalize', statusTextColor[inc.status] || 'text-zinc-500')}>
											<Circle className="h-1.5 w-1.5 fill-current" />
											{inc.status}
										</span>
									</td>
									<td className="py-2.5 px-3 text-xs text-zinc-400 tabular-nums">{timeAgo(inc.created_at)}</td>
									<td className="py-2.5 px-3 text-xs text-zinc-500">
										{inc.assigned_to || <span className="text-zinc-300">—</span>}
									</td>
									<td className="py-2.5 px-3 text-right">
										{hoveredRow === inc.incident_id && inc.status === 'open' ? (
											<button onClick={(e) => handleAck(e, inc.incident_id)} className="text-[11px] font-medium text-amber-600 hover:text-amber-700">
												Ack
											</button>
										) : (
											<Link to={`/incidents/${inc.incident_id}`} className="text-zinc-300 opacity-0 group-hover:opacity-100 transition-opacity">
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
	);
}
