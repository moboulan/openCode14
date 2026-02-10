import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, Circle, Send, RefreshCw, Sparkles, ChevronDown, ChevronUp, Brain, BookOpen } from 'lucide-react';
import { getIncident, updateIncident, getIncidentSuggestions } from '../services/api';
import { timeAgo, formatDate, formatSeconds } from '../utils/formatters';
import { cn } from '../lib/utils';

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

function buildTimeline(incident) {
	const events = [];
	if (incident.created_at) {
		events.push({ label: 'Created', detail: `Alert fired for ${incident.service}`, time: incident.created_at });
	}
	if (incident.assigned_to) {
		events.push({ label: `Paged ${incident.assigned_to}`, detail: 'On-call notified', time: incident.created_at });
	}
	if (incident.acknowledged_at) {
		events.push({ label: 'Acknowledged', detail: `${incident.assigned_to || 'Engineer'} responded`, time: incident.acknowledged_at });
	}
	if (incident.notes?.length) {
		incident.notes.forEach((note) => {
			events.push({ label: 'Note', detail: typeof note === 'string' ? note : JSON.stringify(note), time: null });
		});
	}
	if (incident.resolved_at) {
		events.push({ label: 'Resolved', detail: 'Systems recovered', time: incident.resolved_at });
	}
	return events;
}

export default function IncidentDetail() {
	const { incidentId } = useParams();
	const navigate = useNavigate();
	const [incident, setIncident] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [noteText, setNoteText] = useState('');
	const [submitting, setSubmitting] = useState(false);
	const [suggestions, setSuggestions] = useState([]);
	const [suggestionsLoading, setSuggestionsLoading] = useState(false);
	const [expandedSuggestion, setExpandedSuggestion] = useState(0);

	useEffect(() => {
		(async () => {
			try {
				const inc = await getIncident(incidentId);
				setIncident(inc);
				// fetch AI suggestions
				setSuggestionsLoading(true);
				try {
					const sug = await getIncidentSuggestions(inc.id || incidentId);
					setSuggestions(Array.isArray(sug) ? sug : []);
				} catch { setSuggestions([]); }
				finally { setSuggestionsLoading(false); }
			} catch (err) {
				setError(err.response?.data?.detail || 'Incident not found');
			} finally {
				setLoading(false);
			}
		})();
	}, [incidentId]);

	const handleStatusChange = async (newStatus) => {
		try { setIncident(await updateIncident(incidentId, { status: newStatus })); } catch (e) { console.error(e); }
	};

	const handleAddNote = async () => {
		if (!noteText.trim()) return;
		setSubmitting(true);
		try { setIncident(await updateIncident(incidentId, { note: noteText.trim() })); setNoteText(''); } finally { setSubmitting(false); }
	};

	if (loading) return <div className="flex h-[60vh] items-center justify-center"><RefreshCw className="h-5 w-5 animate-spin text-zinc-300" /></div>;
	if (error || !incident) return (
		<div className="flex h-[60vh] flex-col items-center justify-center gap-2">
			<AlertTriangle className="h-8 w-8 text-zinc-300" />
			<p className="text-sm text-zinc-500">{error || 'Not found'}</p>
			<button onClick={() => navigate('/incidents')} className="text-sm text-blue-600 hover:underline">Back to Incidents</button>
		</div>
	);

	const timeline = buildTimeline(incident);
	const mtta = incident.acknowledged_at && incident.created_at ? (new Date(incident.acknowledged_at) - new Date(incident.created_at)) / 1000 : null;
	const mttr = incident.resolved_at && incident.created_at ? (new Date(incident.resolved_at) - new Date(incident.created_at)) / 1000 : null;

	return (
		<div className="fade-in space-y-5">
			<Link to="/incidents" className="inline-flex items-center gap-1 text-sm text-zinc-400 hover:text-zinc-600 transition-colors">
				<ArrowLeft className="h-3.5 w-3.5" /> Incidents
			</Link>

			{/* Header row */}
			<div className="flex items-start justify-between">
				<div className="space-y-1">
					<div className="flex items-center gap-2">
						<span className={cn('inline-block h-2.5 w-2.5 rounded-full', sevDotColor[incident.severity] || 'bg-zinc-300')} />
						<span className="font-mono text-xs text-zinc-400">{incident.incident_id.slice(0, 8).toUpperCase()}</span>
						<span className={cn('inline-flex items-center gap-1 text-xs font-medium capitalize', statusTextColor[incident.status] || 'text-zinc-500')}>
							<Circle className="h-1.5 w-1.5 fill-current" /> {incident.status}
						</span>
					</div>
					<h1 className="text-lg font-semibold text-zinc-900">{incident.title}</h1>
					<p className="text-sm text-zinc-500">{incident.description || 'No description'}</p>
				</div>
				<div className="flex gap-2">
					{incident.status === 'open' && (
						<button onClick={() => handleStatusChange('acknowledged')} className="rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors">Acknowledge</button>
					)}
					{['open', 'acknowledged', 'investigating'].includes(incident.status) && (
						<button onClick={() => handleStatusChange('resolved')} className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 transition-colors">Resolve</button>
					)}
				</div>
			</div>

			{/* Two-column layout */}
			<div className="grid grid-cols-[1fr_280px] gap-6">
				{/* Left: AI suggestions + timeline + notes */}
				<div className="space-y-5">
					{/* AI Suggestions panel */}
					<div className="rounded-lg border border-indigo-200 bg-gradient-to-br from-indigo-50/80 to-white p-5">
						<div className="mb-3 flex items-center gap-2">
							<Sparkles className="h-4 w-4 text-indigo-500" />
							<h2 className="text-sm font-medium text-indigo-900">AI Root-Cause Analysis</h2>
							{suggestionsLoading && <RefreshCw className="ml-auto h-3.5 w-3.5 animate-spin text-indigo-300" />}
						</div>
						{!suggestionsLoading && suggestions.length === 0 && (
							<p className="text-xs text-zinc-400">No suggestions available for this incident yet.</p>
						)}
						{suggestions.length > 0 && (
							<div className="space-y-2">
								{suggestions.map((s, idx) => {
									const isExpanded = expandedSuggestion === idx;
									const confPct = Math.round(s.confidence * 100);
									const isKb = s.source === 'knowledge_base';
									return (
										<div
											key={idx}
											className={cn(
												'rounded-md border bg-white transition-shadow',
												isExpanded ? 'border-indigo-300 shadow-sm' : 'border-zinc-200'
											)}
										>
											<button
												onClick={() => setExpandedSuggestion(isExpanded ? -1 : idx)}
												className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
											>
												{isKb
													? <BookOpen className="h-3.5 w-3.5 shrink-0 text-indigo-400" />
													: <Brain className="h-3.5 w-3.5 shrink-0 text-purple-400" />
												}
												<span className="flex-1 text-sm font-medium text-zinc-800 truncate">{s.root_cause}</span>
												<span className={cn(
													'shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold tabular-nums',
													confPct >= 50 ? 'bg-emerald-100 text-emerald-700'
														: confPct >= 25 ? 'bg-amber-100 text-amber-700'
															: 'bg-zinc-100 text-zinc-500'
												)}>{confPct}%</span>
												{isExpanded ? <ChevronUp className="h-3.5 w-3.5 text-zinc-400" /> : <ChevronDown className="h-3.5 w-3.5 text-zinc-400" />}
											</button>
											{isExpanded && (
												<div className="border-t border-zinc-100 px-3 py-3 space-y-2">
													<div>
														<p className="text-[11px] font-medium text-zinc-400 uppercase tracking-wide">Recommended Solution</p>
														<p className="mt-1 text-sm text-zinc-700 whitespace-pre-line leading-relaxed">{s.solution}</p>
													</div>
													<div className="flex items-center gap-3 pt-1">
														<span className={cn(
															'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium',
															isKb ? 'bg-indigo-50 text-indigo-600' : 'bg-purple-50 text-purple-600'
														)}>
															{isKb ? <BookOpen className="h-2.5 w-2.5" /> : <Brain className="h-2.5 w-2.5" />}
															{isKb ? 'Knowledge Base' : 'Historical Match'}
														</span>
														{s.matched_pattern && (
															<span className="text-[10px] text-zinc-400 truncate max-w-[200px]">
																matched: {s.matched_pattern}
															</span>
														)}
													</div>
												</div>
											)}
										</div>
									);
								})}
							</div>
						)}
					</div>

					<div className="rounded-lg border border-zinc-200 bg-white p-5">
						<h2 className="mb-4 text-sm font-medium text-zinc-900">Activity</h2>
						<div className="space-y-0">
							{timeline.map((ev, idx) => (
								<div key={idx} className="relative flex gap-3 pb-5 last:pb-0">
									{idx < timeline.length - 1 && <div className="absolute left-[5px] top-[14px] h-[calc(100%-6px)] w-px bg-zinc-200" />}
									<div className="relative z-10 mt-1 h-[10px] w-[10px] shrink-0 rounded-full border-2 border-zinc-300 bg-white" />
									<div className="min-w-0 flex-1">
										<p className="text-sm font-medium text-zinc-800">{ev.label}</p>
										<p className="mt-0.5 text-xs text-zinc-500 break-all">{ev.detail}</p>
										{ev.time && <p className="mt-0.5 text-[11px] text-zinc-400">{formatDate(ev.time)}</p>}
									</div>
								</div>
							))}
						</div>
					</div>

					{/* Note input */}
					<div className="flex gap-2">
						<input
							type="text"
							placeholder="Add a note..."
							value={noteText}
							onChange={(e) => setNoteText(e.target.value)}
							onKeyDown={(e) => e.key === 'Enter' && handleAddNote()}
							className="flex-1 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-700 placeholder-zinc-400 outline-none focus:border-zinc-400 focus:ring-1 focus:ring-zinc-200"
						/>
						<button
							onClick={handleAddNote}
							disabled={submitting || !noteText.trim()}
							className="flex items-center gap-1 rounded-md bg-zinc-800 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-700 disabled:opacity-40"
						>
							<Send className="h-3 w-3" /> Send
						</button>
					</div>
				</div>

				{/* Right: metadata */}
				<div className="space-y-4">
					{/* Response metrics */}
					<div className="rounded-lg border border-zinc-200 bg-white p-4">
						<h3 className="mb-3 text-xs font-medium text-zinc-500">Response</h3>
						<div className="grid grid-cols-2 gap-3">
							<div>
								<p className="text-[11px] text-zinc-400">MTTA</p>
								<p className="text-base font-semibold text-zinc-900 tabular-nums">{formatSeconds(mtta)}</p>
							</div>
							<div>
								<p className="text-[11px] text-zinc-400">MTTR</p>
								<p className="text-base font-semibold text-zinc-900 tabular-nums">{formatSeconds(mttr)}</p>
							</div>
						</div>
					</div>

					{/* Properties */}
					<div className="rounded-lg border border-zinc-200 bg-white p-4">
						<h3 className="mb-3 text-xs font-medium text-zinc-500">Properties</h3>
						<dl className="space-y-2.5 text-sm">
							{[
								['Severity', <span className="flex items-center gap-1.5 capitalize"><span className={cn('h-2 w-2 rounded-full', sevDotColor[incident.severity])} />{incident.severity}</span>],
								['Service', incident.service],
								['Assignee', incident.assigned_to || <span className="text-zinc-300">—</span>],
								['Created', formatDate(incident.created_at)],
							].map(([label, value]) => (
								<div key={label} className="flex items-center justify-between">
									<dt className="text-zinc-400">{label}</dt>
									<dd className="font-medium text-zinc-700">{value}</dd>
								</div>
							))}
						</dl>
					</div>

					{/* Linked Alerts */}
					{incident.alerts?.length > 0 && (
						<div className="rounded-lg border border-zinc-200 bg-white p-4">
							<h3 className="mb-2 text-xs font-medium text-zinc-500">Linked alerts ({incident.alerts.length})</h3>
							<div className="space-y-1.5 max-h-40 overflow-y-auto">
								{incident.alerts.map((alert, idx) => (
									<div key={idx} className="rounded border border-zinc-100 px-2.5 py-1.5">
										<p className="text-xs font-medium text-zinc-700 truncate">{alert.message}</p>
										<p className="text-[11px] text-zinc-400">{alert.service} · {alert.severity}</p>
									</div>
								))}
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}
