export function formatDateTime(value) {
	if (!value) return '—';
	const date = new Date(value);
	return date.toLocaleString();
}

export function formatDuration(seconds) {
	if (seconds === null || seconds === undefined) return '—';
	const mins = Math.floor(seconds / 60);
	const secs = Math.floor(seconds % 60);
	if (mins === 0) return `${secs}s`;
	return `${mins}m ${secs}s`;
}

export function formatRelativeTime(value) {
	if (!value) return '—';
	const now = new Date();
	const date = new Date(value);
	const diffMs = now - date;
	const diffMins = Math.floor(diffMs / 60000);
	if (diffMins < 1) return 'just now';
	if (diffMins < 60) return `${diffMins}m ago`;
	const diffHours = Math.floor(diffMins / 60);
	if (diffHours < 24) return `${diffHours}h ago`;
	const diffDays = Math.floor(diffHours / 24);
	return `${diffDays}d ago`;
}
