from typing import Any, Set
from ..websocket_manager import WebSocketManager
from tools.logger.custom_logging import custom_log

class BroadcastManager:
    def __init__(self, websocket_manager: WebSocketManager):
        self.websocket_manager = websocket_manager

    async def broadcast_to_room(self, room_id: str, event: str, data: Any):
        """Broadcast message to a specific room."""
        self.websocket_manager.broadcast_to_room(room_id, event, data)
        custom_log(f"Broadcast to room {room_id}: {event}")

    async def send_to_session(self, session_id: str, event: str, data: Any):
        """Send message to a specific session."""
        self.websocket_manager.send_to_session(session_id, event, data)
        custom_log(f"Send to session {session_id}: {event}")

    def get_room_members(self, room_id: str) -> Set[str]:
        """Get all members in a room."""
        return self.websocket_manager.get_room_members(room_id)

    def get_rooms_for_session(self, session_id: str) -> Set[str]:
        """Get all rooms for a session."""
        return self.websocket_manager.get_rooms_for_session(session_id) 