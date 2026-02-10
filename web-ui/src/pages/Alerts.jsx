import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Zap, Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { listAlerts, getCorrelationStats } from '@/services/api';
import { timeAgo, severityColor } from '@/utils/formatters';
import { cn } from '@/lib/utils';

const SEVERITIES = ['all', 'critical', 'high', 'medium', 'low', 'info'];

export default function Alerts() {
	const [search, setSearch] = useState('');
	const [severity, setSeverity] = useState('all');
	const [page, setPage] = useState(1);
	const pageSize = 20;

	const { data, isLoading } = useQuery({
		queryKey: ['alerts'],
		queryFn: () => listAlerts({ limit: 200 }),
		refetchInterval: 15000,
	});
	const { data: stats } = useQuery({
		queryKey: ['correlation-stats'],
		queryFn: getCorrelationStats,
		refetchInterval: 30000,
	});

	const allAlerts = Array.isArray(data) ? data : data?.alerts || [];
	const filtered = allAlerts.filter(a => {
		const matchSearch = !search ||
			(a.alert_name || a.message || '').toLowerCase().includes(search.toLowerCase()) ||
			(a.source || a.service || '').toLowerCase().includes(search.toLowerCase());
		const matchSev = severity === 'all' || a.severity === severity;
		return matchSearch && matchSev;
	});
	const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
	const paginated = filtered.slice((page - 1) * pageSize, page * pageSize);

	return (
		<div className="space-y-6 fade-in">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold tracking-tight">Alerts</h1>
					<p className="text-sm text-muted-foreground mt-1">{filtered.length} alert{filtered.length !== 1 ? 's' : ''} ingested</p>
				</div>
				{stats && (
					<div className="flex items-center gap-3">
						{stats.total_alerts != null && <Badge variant="secondary">{stats.total_alerts} total</Badge>}
						{stats.noise_reduction_percentage != null && (
							<Badge variant="success">{Math.round(stats.noise_reduction_percentage)}% noise reduced</Badge>
						)}
					</div>
				)}
			</div>

			{/* Filters */}
			<Card>
				<CardContent className="p-4">
					<div className="flex flex-wrap items-center gap-3">
						<div className="relative flex-1 min-w-50">
							<Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
							<Input placeholder="Search alerts..." value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} className="pl-9" />
						</div>
						<div className="flex items-center gap-2">
							<Filter className="h-4 w-4 text-muted-foreground" />
							<div className="flex gap-1">
								{SEVERITIES.map(s => (
									<button key={s} onClick={() => { setSeverity(s); setPage(1); }}
										className={cn('rounded-md px-2.5 py-1 text-[11px] font-medium capitalize transition-colors border',
											severity === s ? 'bg-primary/15 text-primary border-primary/30' : 'text-muted-foreground hover:text-foreground border-transparent hover:border-border'
										)}>
										{s}
									</button>
								))}
							</div>
						</div>
					</div>
				</CardContent>
			</Card>

			{/* Table */}
			<Card>
				<CardContent className="p-0">
					{isLoading ? (
						<div className="space-y-3 p-5">{[1, 2, 3, 4, 5].map(i => <div key={i} className="shimmer h-12 w-full" />)}</div>
					) : (
						<Table>
							<TableHeader>
								<TableRow>
									<TableHead>Alert Name</TableHead>
									<TableHead className="w-25">Severity</TableHead>
									<TableHead className="w-30">Source</TableHead>
									<TableHead className="w-30">Service</TableHead>
									<TableHead className="w-25">Status</TableHead>
									<TableHead className="w-32.5 text-right">Received</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{paginated.map((a, i) => (
									<TableRow key={a.alert_id || i}>
										<TableCell>
											<div className="flex items-center gap-2">
												<Zap className={cn('h-3.5 w-3.5 shrink-0', severityColor[a.severity]?.text || 'text-yellow-400')} />
												<span className="font-medium text-sm truncate max-w-90">{a.alert_name || a.message || 'Unnamed alert'}</span>
											</div>
										</TableCell>
										<TableCell>
											<span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase', severityColor[a.severity]?.badge)}>
												{a.severity}
											</span>
										</TableCell>
										<TableCell className="text-xs text-muted-foreground">{a.source || '—'}</TableCell>
										<TableCell className="text-xs text-muted-foreground">{a.service || '—'}</TableCell>
										<TableCell>
											<Badge variant={a.incident_id ? 'success' : 'outline'} className="text-[10px]">
												{a.incident_id ? 'correlated' : 'new'}
											</Badge>
										</TableCell>
										<TableCell className="text-xs text-muted-foreground text-right">{timeAgo(a.created_at || a.timestamp)}</TableCell>
									</TableRow>
								))}
								{paginated.length === 0 && (
									<TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-12">No alerts match your filters</TableCell></TableRow>
								)}
							</TableBody>
						</Table>
					)}
				</CardContent>
			</Card>

			{/* Pagination */}
			{totalPages > 1 && (
				<div className="flex items-center justify-between">
					<p className="text-xs text-muted-foreground">Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, filtered.length)} of {filtered.length}</p>
					<div className="flex items-center gap-1">
						<Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft className="h-4 w-4" /></Button>
						{Array.from({ length: totalPages }, (_, i) => i + 1).slice(Math.max(0, page - 3), page + 2).map(p => (
							<Button key={p} variant={p === page ? 'default' : 'outline'} size="sm" className="w-8" onClick={() => setPage(p)}>{p}</Button>
						))}
						<Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}><ChevronRight className="h-4 w-4" /></Button>
					</div>
				</div>
			)}
		</div>
	);
}
