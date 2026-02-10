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
	critical: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', dot: 'bg-red-500', badge: 'bg-red-100 text-red-700' },
	high: { bg: 'bg-orange-50', text: 'text-orange-700', border: 'border-orange-200', dot: 'bg-orange-500', badge: 'bg-orange-100 text-orange-700' },
	medium: { bg: 'bg-yellow-50', text: 'text-yellow-700', border: 'border-yellow-200', dot: 'bg-yellow-500', badge: 'bg-amber-100 text-amber-700' },
	low: { bg: 'bg-blue-50', text: 'text-blue-700', border: 'border-blue-200', dot: 'bg-blue-500', badge: 'bg-blue-100 text-blue-700' },
};

export const statusColor = {
	open: 'bg-red-100 text-red-700',
	acknowledged: 'bg-yellow-100 text-yellow-700',
	investigating: 'bg-purple-100 text-purple-700',
	mitigated: 'bg-blue-100 text-blue-700',
	resolved: 'bg-green-100 text-green-700',
	closed: 'bg-gray-100 text-gray-600',
};

export const statusDot = {
	open: 'bg-red-500',
	acknowledged: 'bg-yellow-500',
	investigating: 'bg-purple-500',
	mitigated: 'bg-blue-500',
	resolved: 'bg-green-500',
	closed: 'bg-gray-400',
};
