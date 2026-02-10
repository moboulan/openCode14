"""
WebSocket connection manager for broadcasting incident events to connected clients.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and broadcasts JSON messages."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._connections.append(ws)
        logger.info("WS client connected (%d total)", len(self._connections))

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            if ws in self._connections:
                self._connections.remove(ws)
        logger.info("WS client disconnected (%d total)", len(self._connections))

    async def broadcast(self, event: str, data: dict[str, Any]) -> None:
        """Send a JSON message to every connected client."""
        message = json.dumps({"event": event, "data": data})
        async with self._lock:
            stale: list[WebSocket] = []
            for ws in self._connections:
                try:
                    await ws.send_text(message)
                except Exception:
                    stale.append(ws)
            for ws in stale:
                self._connections.remove(ws)


manager = ConnectionManager()


async def ws_endpoint(websocket: WebSocket) -> None:
    """WebSocket handler – keeps connection alive and removes on disconnect."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep alive – we only broadcast server→client, but must read
            # to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)
