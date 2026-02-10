import axios from 'axios';

const api = axios.create({
	baseURL: '/',
	timeout: Number(import.meta.env.VITE_API_TIMEOUT || 10000),
});

const incidentBase = '/api/incident-management/api/v1';
const oncallBase = '/api/oncall-service/api/v1';
const alertBase = '/api/alert-ingestion/api/v1';
const notificationBase = '/api/notification-service/api/v1';

// ─── Incidents ─────────────────────────────────────────────
export async function listIncidents(params = {}) {
	const { data } = await api.get(`${incidentBase}/incidents`, { params });
	return data;
}

export async function getIncident(incidentId) {
	const { data } = await api.get(`${incidentBase}/incidents/${incidentId}`);
	return data;
}

export async function updateIncident(incidentId, payload) {
	const { data } = await api.patch(`${incidentBase}/incidents/${incidentId}`, payload);
	return data;
}

export async function getIncidentAnalytics() {
	const { data } = await api.get(`${incidentBase}/incidents/analytics`);
	return data;
}

export async function getIncidentMetrics(incidentId) {
	const { data } = await api.get(`${incidentBase}/incidents/${incidentId}/metrics`);
	return data;
}

export async function addIncidentNote(incidentId, payload) {
	const { data } = await api.post(`${incidentBase}/incidents/${incidentId}/notes`, payload);
	return data;
}

// ─── On-Call ───────────────────────────────────────────────
export async function listSchedules() {
	const { data } = await api.get(`${oncallBase}/schedules`);
	return data;
}

export async function getCurrentOncall(params = {}) {
	const { data } = await api.get(`${oncallBase}/oncall/current`, { params });
	return data;
}

export async function getOncallMetrics() {
	const { data } = await api.get(`${oncallBase}/oncall/metrics`);
	return data;
}

// ─── Alerts ────────────────────────────────────────────────
export async function listAlerts(params = {}) {
	const { data } = await api.get(`${alertBase}/alerts`, { params });
	return data;
}

export async function getCorrelationStats() {
	const { data } = await api.get(`${alertBase}/alerts/stats`);
	return data;
}

// ─── Notifications ─────────────────────────────────────────
export async function listNotifications(params = {}) {
	const { data } = await api.get(`${notificationBase}/notifications`, { params });
	return data;
}

// ─── Health Checks ─────────────────────────────────────────
export async function checkServiceHealth(service) {
	try {
		const { data } = await api.get(`/api/${service}/health`, { timeout: 3000 });
		return { service, status: 'up', ...data };
	} catch {
		return { service, status: 'down' };
	}
}

export async function checkAllServices() {
	const services = [
		'alert-ingestion',
		'incident-management',
		'oncall-service',
		'notification-service',
	];
	return Promise.all(services.map(checkServiceHealth));
}

export default api;
