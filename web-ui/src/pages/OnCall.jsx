import { useState, useEffect } from 'react';
import { Users, Clock, RefreshCw, ArrowRightLeft } from 'lucide-react';
import { listSchedules, getCurrentOncall } from '../services/api';
import { cn } from '../lib/utils';

export default function OnCall() {
	const [schedules, setSchedules] = useState([]);
	const [currentOncall, setCurrentOncall] = useState(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		(async () => {
			try {
				const [s, o] = await Promise.allSettled([listSchedules(), getCurrentOncall()]);
				if (s.status === 'fulfilled') setSchedules(s.value.schedules || s.value || []);
				if (o.status === 'fulfilled') setCurrentOncall(o.value);
			} finally { setLoading(false); }
		})();
	}, []);

	if (loading) return <div className="flex h-[60vh] items-center justify-center"><RefreshCw className="h-5 w-5 animate-spin text-zinc-300" /></div>;

	const primary = currentOncall?.primary;
	const secondary = currentOncall?.secondary;
	const team = currentOncall?.team || 'All Teams';

	return (
		<div className="fade-in space-y-5">
			<div>
				<h1 className="text-xl font-semibold text-zinc-900">On-Call</h1>
				<p className="mt-0.5 text-sm text-zinc-400">Current responders and rotation schedules</p>
			</div>

			{/* Current on-call — simple side-by-side, no gradients */}
			<div className="grid grid-cols-2 gap-4">
				<div className="rounded-lg border border-zinc-200 bg-white p-4">
					<p className="text-xs font-medium text-blue-600 mb-3">Primary</p>
					{primary ? (
						<div className="flex items-center gap-3">
							<div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
								{(primary.name || primary.email || '??').slice(0, 2).toUpperCase()}
							</div>
							<div>
								<p className="text-sm font-medium text-zinc-900">{primary.name || primary.email}</p>
								{primary.email && primary.name && <p className="text-xs text-zinc-400">{primary.email}</p>}
								<p className="text-[11px] text-zinc-400">{team}</p>
							</div>
						</div>
					) : (
						<p className="text-sm text-zinc-400">No active schedule</p>
					)}
				</div>

				<div className="rounded-lg border border-zinc-200 bg-white p-4">
					<p className="text-xs font-medium text-zinc-500 mb-3">Secondary</p>
					{secondary ? (
						<div className="flex items-center gap-3">
							<div className="flex h-10 w-10 items-center justify-center rounded-full bg-zinc-200 text-sm font-semibold text-zinc-600">
								{(secondary.name || secondary.email || '??').slice(0, 2).toUpperCase()}
							</div>
							<div>
								<p className="text-sm font-medium text-zinc-900">{secondary.name || secondary.email}</p>
								{secondary.email && secondary.name && <p className="text-xs text-zinc-400">{secondary.email}</p>}
								<p className="text-[11px] text-zinc-400">Backup</p>
							</div>
						</div>
					) : (
						<p className="text-sm text-zinc-400">Not configured</p>
					)}
				</div>
			</div>

			{/* Schedules — table-ish list */}
			<div className="rounded-lg border border-zinc-200 bg-white overflow-hidden">
				<div className="border-b border-zinc-100 px-4 py-3">
					<h2 className="text-sm font-medium text-zinc-900">Rotation Schedules</h2>
				</div>
				{schedules.length === 0 ? (
					<p className="py-12 text-center text-sm text-zinc-400">No schedules configured</p>
				) : (
					<div className="divide-y divide-zinc-50">
						{schedules.map((sched) => {
							const engineers = typeof sched.engineers === 'string' ? JSON.parse(sched.engineers) : sched.engineers || [];
							return (
								<div key={sched.id} className="flex items-center gap-4 px-4 py-3.5 hover:bg-zinc-50/60 transition-colors">
									<div className="min-w-0 flex-1">
										<div className="flex items-center gap-2">
											<p className="text-sm font-medium text-zinc-900">{sched.team}</p>
											<span className="rounded border border-zinc-200 px-1.5 py-0.5 text-[10px] text-zinc-500 capitalize">{sched.rotation_type}</span>
										</div>
										<div className="mt-0.5 flex items-center gap-3 text-[11px] text-zinc-400">
											<span className="flex items-center gap-1"><Users className="h-3 w-3" />{engineers.length} engineers</span>
											<span className="flex items-center gap-1"><ArrowRightLeft className="h-3 w-3" />Esc {sched.escalation_minutes || 15}m</span>
											<span className="flex items-center gap-1"><Clock className="h-3 w-3" />{sched.handoff_hour || 9}:00 {sched.timezone || 'UTC'}</span>
										</div>
									</div>
									<div className="flex -space-x-1">
										{engineers.slice(0, 4).map((eng, idx) => (
											<div key={idx} className="flex h-6 w-6 items-center justify-center rounded-full border border-white bg-zinc-200 text-[9px] font-semibold text-zinc-600" title={eng.name || eng.email}>
												{(eng.name || eng.email || '??').slice(0, 2).toUpperCase()}
											</div>
										))}
										{engineers.length > 4 && (
											<div className="flex h-6 w-6 items-center justify-center rounded-full border border-white bg-zinc-100 text-[9px] text-zinc-500">+{engineers.length - 4}</div>
										)}
									</div>
								</div>
							);
						})}
					</div>
				)}
			</div>
		</div>
	);
}
