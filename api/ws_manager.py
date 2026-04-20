"""
WebSocket connection manager.

All 6 event types from the spec are routed through broadcast():
  price_update      — emitted every 5 s by the price poller
  signal_update     — emitted after each bot cycle
  position_update   — emitted when floating P&L changes > $1
  trade_opened      — emitted immediately when a trade is placed
  trade_closed      — emitted when a position closes (TP/SL/manual)
  bot_status        — emitted on any status change

Dead connections are cleaned up silently to avoid log spam.
"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Send a typed event to every connected client.
        Stale connections are removed without raising.
        """
        if not self._connections:
            return

        message = json.dumps({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        dead: List[WebSocket] = []

        async with self._lock:
            connections_snapshot = list(self._connections)

        for ws in connections_snapshot:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._connections:
                        self._connections.remove(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# ── Global singleton ──────────────────────────────────────────────────────────
ws_manager = ConnectionManager()
