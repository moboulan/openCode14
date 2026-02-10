import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';

/**
 * Connects to the incident-management WebSocket and invalidates React Query
 * caches when incident events arrive, giving instant UI refreshes.
 *
 * Events: incident_created, incident_updated
 */
export function useIncidentWebSocket() {
	const queryClient = useQueryClient();
	const wsRef = useRef(null);
	const reconnectTimer = useRef(null);

	const connect = useCallback(() => {
		if (wsRef.current?.readyState === WebSocket.OPEN) return;

		const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
		const url = `${protocol}//${window.location.host}/ws/`;

		const ws = new WebSocket(url);
		wsRef.current = ws;

		ws.onopen = () => {
			// Clear any pending reconnect
			if (reconnectTimer.current) {
				clearTimeout(reconnectTimer.current);
				reconnectTimer.current = null;
			}
		};

		ws.onmessage = (evt) => {
			try {
				const msg = JSON.parse(evt.data);
				const { event } = msg;

				if (event === 'incident_created' || event === 'incident_updated') {
					// Invalidate all incident-related queries so React Query refetches
					queryClient.invalidateQueries({ queryKey: ['incidents'] });
					queryClient.invalidateQueries({ queryKey: ['analytics'] });
					queryClient.invalidateQueries({ queryKey: ['alerts-recent'] });

					// If an individual incident page is open, refresh it too
					if (msg.data?.incident_id) {
						queryClient.invalidateQueries({ queryKey: ['incident', msg.data.incident_id] });
						queryClient.invalidateQueries({ queryKey: ['suggestions', msg.data.incident_id] });
					}
				}
			} catch {
				// Ignore non-JSON pings
			}
		};

		ws.onclose = () => {
			wsRef.current = null;
			// Reconnect after 3 seconds
			reconnectTimer.current = setTimeout(connect, 3000);
		};

		ws.onerror = () => {
			ws.close();
		};
	}, [queryClient]);

	useEffect(() => {
		connect();

		return () => {
			if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
			if (wsRef.current) {
				wsRef.current.onclose = null; // prevent reconnect on intentional close
				wsRef.current.close();
			}
		};
	}, [connect]);
}
