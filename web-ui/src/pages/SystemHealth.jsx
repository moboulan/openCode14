import { useQuery } from '@tanstack/react-query';
import { Activity, CheckCircle2, XCircle, Server, Brain, Bell, Zap } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { checkAllServices, getAiHealth } from '@/services/api';
import { cn } from '@/lib/utils';

const SERVICE_ICONS = {
	'alert-ingestion': Zap,
	'incident-management': Activity,
	'oncall-service': Server,
	'notification-service': Bell,
	'ai-analysis': Brain,
};

export default function SystemHealth() {
	const { data: services = [], isLoading } = useQuery({
		queryKey: ['service-health'],
		queryFn: checkAllServices,
		refetchInterval: 10000,
	});
	const { data: aiHealth } = useQuery({
		queryKey: ['ai-health'],
		queryFn: getAiHealth,
		refetchInterval: 30000,
	});

	const upCount = services.filter(s => s.status === 'up').length;
	const allUp = upCount === services.length && services.length > 0;

	return (
		<div className="space-y-6 fade-in">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-2xl font-bold tracking-tight">System Health</h1>
					<p className="text-sm text-muted-foreground mt-1">Monitor the status of all platform services</p>
				</div>
				<Badge variant="secondary" className="text-[10px]">Auto-refresh 10s</Badge>
			</div>

			{/* Overall Status */}
			<Card className={cn('border-2', allUp ? 'border-emerald-500/30 bg-emerald-500/[0.03]' : 'border-red-500/30 bg-red-500/[0.03]')}>
				<CardContent className="p-6 text-center">
					{allUp ? (
						<>
							<CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto mb-3" />
							<h2 className="text-lg font-bold text-emerald-400">All Systems Operational</h2>
							<p className="text-sm text-muted-foreground mt-1">{upCount}/{services.length} services running</p>
						</>
					) : (
						<>
							<XCircle className="h-12 w-12 text-red-500 mx-auto mb-3" />
							<h2 className="text-lg font-bold text-red-400">System Degradation Detected</h2>
							<p className="text-sm text-muted-foreground mt-1">{upCount}/{services.length} services running</p>
						</>
					)}
				</CardContent>
			</Card>

			{/* Service Grid */}
			<div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				{isLoading ? (
					[1, 2, 3, 4, 5].map(i => <div key={i} className="shimmer h-32 rounded-lg" />)
				) : (
					services.map(s => {
						const Icon = SERVICE_ICONS[s.service] || Server;
						const isUp = s.status === 'up';
						return (
							<Card key={s.service} className={cn('transition-all hover:border-primary/30', isUp ? '' : 'border-red-500/30')}>
								<CardContent className="p-5">
									<div className="flex items-start justify-between mb-3">
										<div className={cn('flex h-10 w-10 items-center justify-center rounded-xl', isUp ? 'bg-emerald-500/10' : 'bg-red-500/10')}>
											<Icon className={cn('h-5 w-5', isUp ? 'text-emerald-400' : 'text-red-400')} />
										</div>
										<Badge variant={isUp ? 'success' : 'destructive'} className="text-[10px]">
											{isUp ? 'Healthy' : 'Down'}
										</Badge>
									</div>
									<h3 className="font-semibold text-sm">{s.service.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
									{s.version && <p className="text-[11px] text-muted-foreground mt-1">v{s.version}</p>}
									{s.uptime && <p className="text-[11px] text-muted-foreground">Uptime: {s.uptime}</p>}
									<div className="mt-3 flex items-center gap-1.5">
										<span className={cn('h-2 w-2 rounded-full', isUp ? 'bg-emerald-500 animate-pulse' : 'bg-red-500')} />
										<span className="text-[10px] text-muted-foreground">{isUp ? 'Responding normally' : 'Not responding'}</span>
									</div>
								</CardContent>
							</Card>
						);
					})
				)}
			</div>

			{/* AI Service Details */}
			{aiHealth && (
				<Card>
					<CardHeader className="pb-3">
						<div className="flex items-center gap-2">
							<Brain className="h-4 w-4 text-primary" />
							<CardTitle className="text-sm">AI Analysis Service Details</CardTitle>
						</div>
					</CardHeader>
					<CardContent>
						<div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
							{Object.entries(aiHealth).filter(([k]) => !['status'].includes(k)).map(([key, val]) => (
								<div key={key} className="rounded-lg border border-border p-3 text-center">
									<p className="text-sm font-bold">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</p>
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
