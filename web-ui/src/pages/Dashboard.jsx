import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
	AlertTriangle, Clock, CheckCircle2, Timer, Eye,
	Zap, ArrowRight, ShieldAlert, TrendingDown
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { listIncidents, getIncidentAnalytics, checkAllServices, listAlerts } from '@/services/api';
import { timeAgo, formatSeconds, severityColor, statusColor } from '@/utils/formatters';
import { cn } from '@/lib/utils';

function StatCard({ title, value, subtitle, icon: Icon, iconColor }) {
	return (
		<Card className="relative overflow-hidden">
			<CardContent className="p-5">
				<div className="flex items-start justify-between">
					<div className="space-y-1">
						<p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wide">{title}</p>
						<p className="text-2xl font-bold tracking-tight">{value}</p>
						{subtitle && <p className="text-[11px] text-muted-foreground">{subtitle}</p>}
					</div>
					<div className={cn('flex h-10 w-10 items-center justify-center rounded-xl', iconColor || 'bg-primary/10')}>
						<Icon className={cn('h-5 w-5',
							iconColor?.includes('red') ? 'text-red-400' :
								iconColor?.includes('yellow') ? 'text-yellow-400' :
									iconColor?.includes('emerald') ? 'text-emerald-400' :
										iconColor?.includes('blue') ? 'text-blue-400' :
											iconColor?.includes('purple') ? 'text-purple-400' :
												'text-primary'
						)} />
					</div>
				</div>
			</CardContent>
		</Card>
	);
}

export default function Dashboard() {
	const navigate = useNavigate();

	const { data: incidents = [], isLoading: incLoading } = useQuery({
		queryKey: ['incidents'],
		queryFn: () => listIncidents({ limit: 50 }),
		refetchInterval: 15000,
	});
	const { data: analytics, isLoading: analyticsLoading } = useQuery({
		queryKey: ['analytics'],
		queryFn: getIncidentAnalytics,
		refetchInterval: 30000,
	});
	const { data: services = [] } = useQuery({
		queryKey: ['services'],
		queryFn: checkAllServices,
		refetchInterval: 15000,
	});
	const { data: alerts = [] } = useQuery({
		queryKey: ['alerts-recent'],
		queryFn: () => listAlerts({ limit: 10 }),
		refetchInterval: 15000,
	});

	const incidentList = Array.isArray(incidents) ? incidents : incidents?.incidents || [];
	const alertList = Array.isArray(alerts) ? alerts : alerts?.alerts || [];
	const openCount = incidentList.filter(i => i.status === 'open').length;
	const ackedCount = incidentList.filter(i => i.status === 'acknowledged').length;
	const resolvedCount = incidentList.filter(i => i.status === 'resolved' || i.status === 'closed').length;
	const criticalCount = incidentList.filter(i => i.severity === 'critical' && i.status === 'open').length;
	const mtta = analytics?.avg_mtta_seconds;
	const mttr = analytics?.avg_mttr_seconds;
	const recentIncidents = incidentList.slice(0, 8);
	const upServices = services.filter(s => s.status === 'up').length;

	return (
		<div className="space-y-6 fade-in">
			<div>
				<h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
				<p className="text-sm text-muted-foreground mt-1">Real-time overview of incidents, alerts, and platform health</p>
			</div>

			{/* Stats */}
			<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
				<StatCard title="Open" value={incLoading ? '—' : openCount} subtitle={criticalCount > 0 ? `${criticalCount} critical` : undefined} icon={AlertTriangle} iconColor="bg-red-500/10" />
				<StatCard title="Acknowledged" value={incLoading ? '—' : ackedCount} icon={Eye} iconColor="bg-yellow-500/10" />
				<StatCard title="Resolved" value={incLoading ? '—' : resolvedCount} icon={CheckCircle2} iconColor="bg-emerald-500/10" />
				<StatCard title="MTTA" value={analyticsLoading ? '—' : formatSeconds(mtta)} subtitle="Avg acknowledge" icon={Timer} iconColor="bg-blue-500/10" />
				<StatCard title="MTTR" value={analyticsLoading ? '—' : formatSeconds(mttr)} subtitle="Avg resolve" icon={Clock} iconColor="bg-purple-500/10" />
			</div>


			{/* Main Grid */}
			<div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
				{/* Recent Incidents */}
				<Card className="lg:col-span-2">
					<CardHeader className="pb-3">
						<div className="flex items-center justify-between">
							<CardTitle className="text-sm font-semibold">Recent Incidents</CardTitle>
							<Button variant="ghost" size="sm" className="text-xs" onClick={() => navigate('/incidents')}>View all <ArrowRight className="ml-1 h-3 w-3" /></Button>
						</div>
					</CardHeader>
					<CardContent className="p-0">
						{incLoading ? (
							<div className="space-y-3 p-5">{[1, 2, 3].map(i => <div key={i} className="shimmer h-10 w-full" />)}</div>
						) : (
							<Table>
								<TableHeader>
									<TableRow>
										<TableHead>Title</TableHead>
										<TableHead className="w-[90px]">Severity</TableHead>
										<TableHead className="w-[100px]">Status</TableHead>
										<TableHead className="w-[120px] text-right">When</TableHead>
									</TableRow>
								</TableHeader>
								<TableBody>
									{recentIncidents.map(inc => (
										<TableRow key={inc.incident_id} className="cursor-pointer" onClick={() => navigate(`/incidents/${inc.incident_id}`)}>
											<TableCell>
												<div className="flex items-center gap-2">
													<ShieldAlert className={cn('h-3.5 w-3.5 shrink-0', severityColor[inc.severity]?.text || 'text-zinc-400')} />
													<span className="font-medium text-sm truncate max-w-[300px]">{inc.title}</span>
												</div>
											</TableCell>
											<TableCell><span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase', severityColor[inc.severity]?.badge)}>{inc.severity}</span></TableCell>
											<TableCell><span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold capitalize', statusColor[inc.status])}>{inc.status}</span></TableCell>
											<TableCell className="text-right text-xs text-muted-foreground">{timeAgo(inc.created_at)}</TableCell>
										</TableRow>
									))}
									{recentIncidents.length === 0 && (
										<TableRow><TableCell colSpan={4} className="text-center text-sm text-muted-foreground py-8">No incidents found</TableCell></TableRow>
									)}
								</TableBody>
							</Table>
						)}
					</CardContent>
				</Card>

				{/* Recent Alerts */}
				<Card>
					<CardHeader className="pb-3">
						<div className="flex items-center justify-between">
							<CardTitle className="text-sm font-semibold">Recent Alerts</CardTitle>
							<Button variant="ghost" size="sm" className="text-xs" onClick={() => navigate('/alerts')}>View all <ArrowRight className="ml-1 h-3 w-3" /></Button>
						</div>
					</CardHeader>
					<CardContent>
						<div className="space-y-3">
							{alertList.slice(0, 6).map((a, i) => (
								<div key={a.alert_id || i} className="flex items-start gap-3 rounded-lg border border-border p-3 hover:bg-accent/50 transition-colors">
									<Zap className={cn('mt-0.5 h-4 w-4 shrink-0', severityColor[a.severity]?.text || 'text-yellow-400')} />
									<div className="min-w-0 flex-1">
										<p className="text-xs font-medium truncate">{a.alert_name || a.message || 'Alert'}</p>
										<p className="text-[10px] text-muted-foreground mt-0.5">{a.service || a.source || '—'} &middot; {timeAgo(a.created_at || a.timestamp)}</p>
									</div>
									<span className={cn('inline-flex rounded-md border px-1.5 py-0.5 text-[9px] font-semibold uppercase shrink-0', severityColor[a.severity]?.badge)}>{a.severity}</span>
								</div>
							))}
							{alertList.length === 0 && <p className="text-center text-sm text-muted-foreground py-4">No recent alerts</p>}
						</div>
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
