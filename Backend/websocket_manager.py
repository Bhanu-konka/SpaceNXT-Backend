import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps firebase_uid -> Set of active WebSocket objects
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, uid: str):
        await websocket.accept()
        async with self._lock:
            if uid not in self.active_connections:
                self.active_connections[uid] = set()
            self.active_connections[uid].add(websocket)
        print(f"[WebSocket] Connected: UID={uid} (Total connections for UID: {len(self.active_connections[uid])})")

    async def disconnect(self, websocket: WebSocket, uid: str):
        async with self._lock:
            if uid in self.active_connections:
                self.active_connections[uid].discard(websocket)
                if not self.active_connections[uid]:
                    del self.active_connections[uid]
        print(f"[WebSocket] Disconnected: UID={uid}")

    def is_online(self, uid: str) -> bool:
        """Returns True if the UID has at least one active WebSocket connection."""
        return uid in self.active_connections and len(self.active_connections[uid]) > 0

    async def send_personal_message(self, message_data: dict, uid: str) -> bool:
        """
        Sends a JSON message payload to all active WebSocket connections of a specific UID.
        Returns True if delivered to at least one socket, False otherwise.
        """
        if not self.is_online(uid):
            return False

        sockets = list(self.active_connections.get(uid, []))
        delivered_count = 0
        dead_sockets = []

        payload = json.dumps(message_data)

        for ws in sockets:
            try:
                await ws.send_text(payload)
                delivered_count += 1
            except Exception as e:
                print(f"[WebSocket] Error sending to UID={uid}: {e}")
                dead_sockets.append(ws)

        if dead_sockets:
            async with self._lock:
                for dead_ws in dead_sockets:
                    if uid in self.active_connections:
                        self.active_connections[uid].discard(dead_ws)
                        if not self.active_connections[uid]:
                            del self.active_connections[uid]

        return delivered_count > 0

    async def broadcast_to_uids(self, message_data: dict, uids: list[str]):
        """Broadcasts a payload to a list of target UIDs."""
        for target_uid in uids:
            await self.send_personal_message(message_data, target_uid)

manager = ConnectionManager()
