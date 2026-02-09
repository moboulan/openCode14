// ─── API layer ──────────────────────────────────────
import axios from 'axios';

const apiClient = axios.create({
	baseURL: '/',
	timeout: Number(import.meta.env.VITE_API_TIMEOUT || 10000),
});

const incidentBase = '/api/incident-management/api/v1';
const oncallBase = '/api/oncall-service/api/v1';

export async function listIncidents(params = {}) {
	const { data } = await apiClient.get(`${incidentBase}/incidents`, { params });
	return data;
}

export async function getIncident(incidentId) {
	const { data } = await apiClient.get(`${incidentBase}/incidents/${incidentId}`);
	return data;
}

export async function updateIncident(incidentId, payload) {
	const { data } = await apiClient.patch(`${incidentBase}/incidents/${incidentId}`, payload);
	return data;
}

export async function getIncidentAnalytics() {
	const { data } = await apiClient.get(`${incidentBase}/incidents/analytics`);
	return data;
}

export async function getIncidentMetrics(incidentId) {
	const { data } = await apiClient.get(`${incidentBase}/incidents/${incidentId}/metrics`);
	return data;
}

export async function addIncidentNote(incidentId, payload) {
	const { data } = await apiClient.post(`${incidentBase}/incidents/${incidentId}/notes`, payload);
	return data;
}

// ── On-Call ──
export async function listSchedules() {
	const { data } = await apiClient.get(`${oncallBase}/schedules`);
	return data;
}

export async function getCurrentOncall(params = {}) {
	const { data } = await apiClient.get(`${oncallBase}/oncall/current`, { params });
	return data;
}

// ── Metrics Trends ──
export async function getMetricsTrends() {
	const { data } = await apiClient.get(`${incidentBase}/incidents/metrics/trends`);
	return data;
}

