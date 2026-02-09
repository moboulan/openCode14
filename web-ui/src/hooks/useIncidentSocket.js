import { useEffect, useRef, useState } from 'react';

const WS_URL = `${window.location.origin.replace('http', 'ws')}/ws/events`;
const WS_PING_INTERVAL = Number(import.meta.env.VITE_WS_PING_INTERVAL || 30000);
const WS_RECONNECT_INTERVAL = Number(import.meta.env.VITE_WS_RECONNECT_INTERVAL || 3000);

function useIncidentSocket(onEvent) {
	const socketRef = useRef(null);
	const [connected, setConnected] = useState(false);

	useEffect(() => {
		let pingInterval;
		let reconnectTimeout;

		const connect = () => {
			const socket = new WebSocket(WS_URL);
			socketRef.current = socket;

			socket.onopen = () => {
				setConnected(true);
				pingInterval = window.setInterval(() => {
					socket.send('ping');
				}, WS_PING_INTERVAL);
			};

			socket.onmessage = (event) => {
				try {
					const parsed = JSON.parse(event.data);
					if (parsed && onEvent) onEvent(parsed);
				} catch (err) {
					// ignore malformed frames
				}
			};

			socket.onerror = () => {
				socket.close();
			};

			socket.onclose = () => {
				setConnected(false);
				window.clearInterval(pingInterval);
				reconnectTimeout = window.setTimeout(connect, WS_RECONNECT_INTERVAL);
			};
		};

		connect();

		return () => {
			window.clearInterval(pingInterval);
			window.clearTimeout(reconnectTimeout);
			if (socketRef.current) socketRef.current.close();
		};
	}, [onEvent]);

	return { connected };
}

export { useIncidentSocket };
