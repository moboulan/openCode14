import { formatDistanceToNow, format } from 'date-fns';

export function timeAgo(dateStr) {
	if (!dateStr) return '—';
	try {
		return formatDistanceToNow(new Date(dateStr), { addSuffix: true });
	} catch {
		return dateStr;
	}
}

export function formatDate(dateStr) {
	if (!dateStr) return '—';
	try {
		return format(new Date(dateStr), 'MMM d, yyyy HH:mm');
	} catch {
		return dateStr;
	}
}

export function formatSeconds(seconds) {
	if (seconds == null) return '—';
	if (seconds < 60) return `${Math.round(seconds)}s`;
	if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
	return `${(seconds / 3600).toFixed(1)}h`;
}

export const severityColor = {
	critical: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', dot: 'bg-red-500', badge: 'bg-red-500/15 text-red-400 border-red-500/20' },
	high: { bg: 'bg-orange-500/10', text: 'text-orange-400', border: 'border-orange-500/20', dot: 'bg-orange-500', badge: 'bg-orange-500/15 text-orange-400 border-orange-500/20' },
	medium: { bg: 'bg-yellow-500/10', text: 'text-yellow-400', border: 'border-yellow-500/20', dot: 'bg-yellow-500', badge: 'bg-amber-500/15 text-amber-400 border-amber-500/20' },
	low: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/20', dot: 'bg-blue-500', badge: 'bg-blue-500/15 text-blue-400 border-blue-500/20' },
	info: { bg: 'bg-sky-500/10', text: 'text-sky-400', border: 'border-sky-500/20', dot: 'bg-sky-500', badge: 'bg-sky-500/15 text-sky-400 border-sky-500/20' },
};

export const statusColor = {
	open: 'bg-red-500/15 text-red-400 border-red-500/20',
	acknowledged: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/20',
	investigating: 'bg-purple-500/15 text-purple-400 border-purple-500/20',
	mitigated: 'bg-blue-500/15 text-blue-400 border-blue-500/20',
	resolved: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
	closed: 'bg-zinc-500/15 text-zinc-400 border-zinc-500/20',
};

export const statusDot = {
	open: 'bg-red-500',
	acknowledged: 'bg-yellow-500',
	investigating: 'bg-purple-500',
	mitigated: 'bg-blue-500',
	resolved: 'bg-emerald-500',
	closed: 'bg-zinc-400',
};
