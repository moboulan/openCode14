import { useEffect, useCallback, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getIncident, getIncidentMetrics, updateIncident, addIncidentNote } from '@/services/api';
import { formatDateTime, formatDuration } from '@/utils/formatters';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import {
	ChevronRight, CheckCircle2, ShieldAlert, Timer, TrendingUp,
	Clock, AlertCircle, User, Send,
} from 'lucide-react';

function Timeline({ events = [] }) {
	if (!events.length) return <p className="text-sm text-muted-foreground py-4">No timeline yet.</p>;
	return (
		<div className="relative space-y-4 pl-6 pt-2">
			<div className="absolute left-2 top-3 bottom-3 w-px bg-border" />
			{events.map((item, idx) => (
				<div key={`${item.event}-${idx}`} className="relative flex items-start gap-3">
					<div className="absolute -left-4 top-1 flex h-4 w-4 items-center justify-center rounded-full border bg-background">
						<div className="h-1.5 w-1.5 rounded-full bg-foreground" />
					</div>
					<div className="flex flex-col">
						<span className="text-sm font-medium capitalize">{item.event}</span>
						<span className="text-xs text-muted-foreground">{formatDateTime(item.timestamp)}</span>
					</div>
				</div>
			))}
		</div>
	);
}

function AlertList({ alerts = [] }) {
	if (!alerts.length) return <p className="text-sm text-muted-foreground py-4">No linked alerts.</p>;
	return (
		<div className="space-y-2 pt-2">
			{alerts.map((alert) => (
				<div key={alert.alert_id} className="flex flex-col gap-0.5 rounded-md border border-border p-3">
					<span className="text-sm font-medium">{alert.message}</span>
					<div className="flex items-center gap-2 text-xs text-muted-foreground">
						<code>{alert.service}</code>
						<Badge variant={alert.severity} className="text-[10px] px-1.5 py-0">{alert.severity}</Badge>
						<span>{formatDateTime(alert.timestamp)}</span>
					</div>
				</div>
			))}
		</div>
	);
}

function NotesList({ notes = [] }) {
	if (!notes.length) return <p className="text-sm text-muted-foreground py-4">No notes yet.</p>;
	return (
		<div className="space-y-2 pt-2">
			{notes.map((note, idx) => (
				<div key={idx} className="rounded-md border border-border p-3">
					<p className="text-sm">{note.content}</p>
					<span className="text-xs text-muted-foreground">{note.author} · {formatDateTime(note.created_at)}</span>
				</div>
			))}
		</div>
	);
}

export default function IncidentDetail() {
	const { incidentId } = useParams();
	const [incident, setIncident] = useState(null);
	const [metrics, setMetrics] = useState(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);
	const [actionStatus, setActionStatus] = useState('');
	const [activeTab, setActiveTab] = useState('timeline');
	const [noteText, setNoteText] = useState('');

	const loadIncident = useCallback(async () => {
		try {
			setLoading(true);
			const data = await getIncident(incidentId);
			setIncident(data);
			setError(null);
		} catch {
			setError('Incident not found');
		} finally {
			setLoading(false);
		}
	}, [incidentId]);

	const loadMetrics = useCallback(async () => {
		try {
			const data = await getIncidentMetrics(incidentId);
			setMetrics(data);
		} catch { }
	}, [incidentId]);

	useEffect(() => {
		loadIncident();
		loadMetrics();
	}, [loadIncident, loadMetrics]);

	const handleUpdate = async (status) => {
		try {
			setActionStatus('Saving…');
			const updated = await updateIncident(incidentId, { status });
			setIncident(updated);
			loadMetrics();
			setActionStatus('');
		} catch {
			setActionStatus('Failed to update');
		}
	};

	const handleAddNote = async () => {
		if (!noteText.trim()) return;
		try {
			await addIncidentNote(incidentId, { content: noteText.trim(), author: 'operator' });
			setNoteText('');
			loadIncident();
		} catch { }
	};

	if (loading && !incident) {
		return <p className="text-sm text-muted-foreground animate-pulse">Loading incident…</p>;
	}
	if (error) {
		return (
			<div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
				{error}
			</div>
		);
	}
	if (!incident) return null;

	const metricCards = metrics ? [
		{ label: 'MTTA', value: formatDuration(metrics.mtta_seconds), icon: Timer, color: 'text-cyan-500' },
		{ label: 'MTTR', value: formatDuration(metrics.mttr_seconds), icon: TrendingUp, color: 'text-yellow-500' },
		{ label: 'Created', value: formatDateTime(metrics.created_at), icon: Clock, color: 'text-muted-foreground' },
		{ label: 'Resolved', value: formatDateTime(metrics.resolved_at), icon: CheckCircle2, color: 'text-status-resolved' },
	] : [];

	const tabs = [
		{ key: 'timeline', label: 'Timeline', count: incident.timeline?.length },
		{ key: 'alerts', label: 'Alerts', count: incident.alerts?.length },
		{ key: 'notes', label: 'Notes', count: incident.notes?.length },
	];

	return (
		<div className="space-y-6">
			{/* Breadcrumb */}
			<nav className="flex items-center gap-1 text-sm text-muted-foreground">
				<Link to="/" className="hover:text-foreground transition-colors">Dashboard</Link>
				<ChevronRight className="h-3.5 w-3.5" />
				<span className="font-mono text-foreground">{incident.incident_id}</span>
			</nav>

			{/* Header card */}
			<Card>
				<CardContent className="p-5">
					<div className="flex flex-wrap items-start justify-between gap-4">
						<div className="space-y-2">
							<h2 className="text-lg font-bold">{incident.title}</h2>
							<div className="flex flex-wrap items-center gap-2">
								<Badge variant={incident.severity}>{incident.severity}</Badge>
								<Badge variant={incident.status}>{incident.status}</Badge>
								<code className="text-xs text-muted-foreground">{incident.service}</code>
							</div>
						</div>
						<div className="flex gap-2">
							<Button
								variant="outline"
								size="sm"
								onClick={() => handleUpdate('acknowledged')}
								disabled={incident.status === 'acknowledged' || incident.status === 'resolved'}
							>
								<ShieldAlert className="mr-1.5 h-3.5 w-3.5" />
								Acknowledge
							</Button>
							<Button
								variant="destructive"
								size="sm"
								onClick={() => handleUpdate('resolved')}
								disabled={incident.status === 'resolved'}
							>
								<CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />
								Resolve
							</Button>
						</div>
					</div>

					<div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
						<div>
							<span className="text-xs text-muted-foreground flex items-center gap-1"><User className="h-3 w-3" /> Assigned</span>
							<span className="text-sm font-medium">{incident.assigned_to || 'Unassigned'}</span>
						</div>
						<div>
							<span className="text-xs text-muted-foreground flex items-center gap-1"><Clock className="h-3 w-3" /> Created</span>
							<span className="text-sm font-medium">{formatDateTime(incident.created_at)}</span>
						</div>
						<div>
							<span className="text-xs text-muted-foreground flex items-center gap-1"><AlertCircle className="h-3 w-3" /> Acknowledged</span>
							<span className="text-sm font-medium">{formatDateTime(incident.acknowledged_at)}</span>
						</div>
						<div>
							<span className="text-xs text-muted-foreground flex items-center gap-1"><CheckCircle2 className="h-3 w-3" /> Resolved</span>
							<span className="text-sm font-medium">{formatDateTime(incident.resolved_at)}</span>
						</div>
					</div>

					{actionStatus && (
						<p className="mt-2 text-xs text-muted-foreground">{actionStatus}</p>
					)}
				</CardContent>
			</Card>

			{/* Metrics */}
			{metricCards.length > 0 && (
				<div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
					{metricCards.map((m) => (
						<Card key={m.label}>
							<CardContent className="flex items-center justify-between p-4">
								<div>
									<p className="text-xs text-muted-foreground">{m.label}</p>
									<p className={`text-sm font-bold font-mono ${m.color}`}>{m.value}</p>
								</div>
								<m.icon className={`h-4 w-4 ${m.color}`} />
							</CardContent>
						</Card>
					))}
				</div>
			)}

			{/* Tabbed content */}
			<Card>
				<CardHeader className="pb-0">
					<Tabs>
						<TabsList>
							{tabs.map(t => (
								<TabsTrigger
									key={t.key}
									active={activeTab === t.key}
									onClick={() => setActiveTab(t.key)}
								>
									{t.label}
									{t.count != null && (
										<span className="ml-1 font-mono text-[10px] opacity-60">({t.count})</span>
									)}
								</TabsTrigger>
							))}
						</TabsList>
					</Tabs>
				</CardHeader>
				<CardContent>
					{activeTab === 'timeline' && <Timeline events={incident.timeline} />}
					{activeTab === 'alerts' && <AlertList alerts={incident.alerts} />}
					{activeTab === 'notes' && (
						<div className="space-y-3">
							<NotesList notes={incident.notes} />
							<div className="flex gap-2">
								<Input
									value={noteText}
									onChange={(e) => setNoteText(e.target.value)}
									onKeyDown={(e) => e.key === 'Enter' && handleAddNote()}
									placeholder="Add a note…"
								/>
								<Button size="sm" onClick={handleAddNote} disabled={!noteText.trim()}>
									<Send className="mr-1.5 h-3.5 w-3.5" />
									Add
								</Button>
							</div>
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	);
}
