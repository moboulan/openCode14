// ─── API layer ──────────────────────────────────────
const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

import axios from 'axios';
import * as mock from './mockData.js';

const apiClient = axios.create({
	baseURL: '/',
	timeout: Number(import.meta.env.VITE_API_TIMEOUT || 10000),
});

const incidentBase = '/api/incident-management/api/v1';
const oncallBase = '/api/oncall-service/api/v1';

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

// ── Metrics Trends ──
export async function getMetricsTrends() {
	if (USE_MOCK) return mock.getMetricsTrends();
	const { data } = await apiClient.get(`${incidentBase}/incidents/metrics/trends`);
	return data;
}

