// ─── API layer ──────────────────────────────────────
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

import axios from 'axios';
import * as mock from './mockData.js';

const apiClient = axios.create({
	baseURL: '/',
	timeout: Number(import.meta.env.VITE_API_TIMEOUT || 10000),
});

const alertIngestionBase = '/api/alert-ingestion/api/v1';
const incidentBase = '/api/incident-management/api/v1';
const oncallBase = '/api/oncall-service/api/v1';
const notificationBase = '/api/notification-service/api/v1';

// ── Alerts ──
export async function listAlerts(params = {}) {
	if (USE_MOCK) return mock.listAlerts(params);
	const { data } = await apiClient.get(`${alertIngestionBase}/alerts`, { params });
	return data;
}

export async function createAlert(payload) {
	if (USE_MOCK) return mock.createAlert(payload);
	const { data } = await apiClient.post(`${alertIngestionBase}/alerts`, payload);
	return data;
}

export async function getAlert(alertId) {
	if (USE_MOCK) return mock.getAlert(alertId);
	const { data } = await apiClient.get(`${alertIngestionBase}/alerts/${alertId}`);
	return data;
}

// ── Incidents ──
export async function createIncident(payload) {
	if (USE_MOCK) return mock.createIncident(payload);
	const { data } = await apiClient.post(`${incidentBase}/incidents`, payload);
	return data;
}

export async function listIncidents(params = {}) {
	if (USE_MOCK) return mock.listIncidents(params);
	const { data } = await apiClient.get(`${incidentBase}/incidents`, { params });
	return data;
}

export async function getIncident(incidentId) {
	if (USE_MOCK) return mock.getIncident(incidentId);
	const { data } = await apiClient.get(`${incidentBase}/incidents/${incidentId}`);
	return data;
}

export async function updateIncident(incidentId, payload) {
	if (USE_MOCK) return mock.updateIncident(incidentId, payload);
	const { data } = await apiClient.patch(`${incidentBase}/incidents/${incidentId}`, payload);
	return data;
}

export async function getIncidentAnalytics() {
	if (USE_MOCK) return mock.getIncidentAnalytics();
	const { data } = await apiClient.get(`${incidentBase}/incidents/analytics`);
	return data;
}

export async function getIncidentMetrics(incidentId) {
	if (USE_MOCK) return mock.getIncidentMetrics(incidentId);
	const { data } = await apiClient.get(`${incidentBase}/incidents/${incidentId}/metrics`);
	return data;
}

export async function addIncidentNote(incidentId, payload) {
	if (USE_MOCK) return mock.addIncidentNote(incidentId, payload);
	const { data } = await apiClient.post(`${incidentBase}/incidents/${incidentId}/notes`, payload);
	return data;
}

// ── On-Call ──
export async function listSchedules() {
	if (USE_MOCK) return mock.listSchedules();
	const { data } = await apiClient.get(`${oncallBase}/schedules`);
	return data;
}

export async function getCurrentOncall(params = {}) {
	if (USE_MOCK) return mock.getCurrentOncall(params);
	const { data } = await apiClient.get(`${oncallBase}/oncall/current`, { params });
	return data;
}

export async function escalateIncident(payload) {
	if (USE_MOCK) return mock.escalateIncident(payload);
	const { data } = await apiClient.post(`${oncallBase}/escalate`, payload);
	return data;
}

// ── Notifications ──
export async function listNotifications(params = {}) {
	if (USE_MOCK) return mock.listNotifications(params);
	const { data } = await apiClient.get(`${notificationBase}/notifications`, { params });
	return data;
}

export async function sendNotification(payload) {
	if (USE_MOCK) return mock.sendNotification(payload);
	const { data } = await apiClient.post(`${notificationBase}/notify`, payload);
	return data;
}

// ── Metrics Trends ──
export async function getMetricsTrends() {
	if (USE_MOCK) return mock.getMetricsTrends();
	const { data } = await apiClient.get(`${incidentBase}/incidents/metrics/trends`);
	return data;
}

export { apiClient };
