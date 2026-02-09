import { useEffect, useRef, useState } from 'react';

const WS_URL = `${window.location.origin.replace('http', 'ws')}/ws/events`;

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
        }, 30000);
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
        reconnectTimeout = window.setTimeout(connect, 3000);
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
