from flask import request
from core.managers.websocket_manager import WebSocketManager
from core.managers.redis_manager import RedisManager
from core.managers.jwt_manager import JWTManager
from tools.logger.custom_logging import custom_log
from typing import Dict, Any, Optional, Set
from flask_cors import CORS
import time
from datetime import datetime
from utils.config.config import Config
from core.modules.base_module import BaseModule
from .components.room_manager import RoomManager, RoomPermission
from .components.session_manager import SessionManager
from .components.event_handler import EventHandler
from .components.result_handler import ResultHandler
from .components.broadcast_manager import BroadcastManager

class WebSocketModule(BaseModule):
    def __init__(self, app_manager=None):
        super().__init__(app_manager)
        self.websocket_manager = WebSocketManager()
        self.redis_manager = RedisManager()
        self.jwt_manager = JWTManager()
        
        # Set JWT manager in WebSocket manager
        self.websocket_manager.set_jwt_manager(self.jwt_manager)
        
        # Initialize components
        self.room_manager = RoomManager()
        self.session_manager = SessionManager(self.redis_manager, self.jwt_manager)
        self.result_handler = ResultHandler()
        self.broadcast_manager = BroadcastManager(self.websocket_manager)
        self.event_handler = EventHandler(
            self.websocket_manager,
            self.room_manager,
            self.session_manager,
            self.redis_manager,
            self.result_handler,
            self.broadcast_manager
        )
        
        # Set room access check function
        self.websocket_manager.set_room_access_check(self.room_manager.check_room_access)
        
        custom_log("WebSocketModule initialized")

    def initialize(self, app_manager):
        """
        Initialize the WebSocket module with the AppManager.
        
        :param app_manager: AppManager instance
        """
        super().initialize(app_manager)
        
        if app_manager and app_manager.flask_app:
            self.websocket_manager.initialize(app_manager.flask_app)
        
        # Initialize CORS settings
        self._setup_cors()
        
        # Register WebSocket handlers
        self._register_handlers()
        
        # Mark as initialized
        self._initialized = True
        custom_log("WebSocketModule initialization complete")

    def _setup_cors(self):
        """Configure CORS settings with security measures."""
        # Use allowed origins from Config
        allowed_origins = Config.WS_ALLOWED_ORIGINS
        
        # Configure CORS with specific origins
        self.websocket_manager.set_cors_origins(allowed_origins)
        custom_log(f"WebSocket CORS configured for origins: {allowed_origins}")

    def _register_handlers(self):
        """Register all WebSocket event handlers."""
        # Connect and disconnect don't use authentication
        self.websocket_manager.register_handler('connect', self.event_handler.handle_connect)
        self.websocket_manager.register_handler('disconnect', self.event_handler.handle_disconnect)
        
        # All other handlers use authentication
        self.websocket_manager.register_authenticated_handler('join_room', self.event_handler.handle_join)
        self.websocket_manager.register_authenticated_handler('leave', self.event_handler.handle_leave)
        self.websocket_manager.register_authenticated_handler('message', self.event_handler.handle_message)
        self.websocket_manager.register_authenticated_handler('get_users', self.event_handler.handle_get_users)
        self.websocket_manager.register_authenticated_handler('create_room', self.event_handler.handle_create_room)
        
        # Game-related handlers are now registered in the game plugin
        # This makes the code more modular and easier to maintain
        
        custom_log("WebSocket event handlers registered")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the WebSocket module.
        
        :return: Dictionary containing health status
        """
        base_health = super().health_check()
        
        # Add WebSocket-specific health checks
        websocket_health = {
            'websocket_manager': 'healthy' if self.websocket_manager else 'not_initialized',
            'room_manager': 'healthy' if self.room_manager else 'not_initialized',
            'session_manager': 'healthy' if self.session_manager else 'not_initialized',
            'event_handler': 'healthy' if self.event_handler else 'not_initialized',
            'broadcast_manager': 'healthy' if self.broadcast_manager else 'not_initialized',
        }
        
        base_health.update(websocket_health)
        return base_health

    def broadcast_to_room(self, room_id: str, event: str, data: Any):
        """Broadcast message to a specific room."""
        self.broadcast_manager.broadcast_to_room(room_id, event, data)

    def send_to_session(self, session_id: str, event: str, data: Any):
        """Send message to a specific session."""
        self.broadcast_manager.send_to_session(session_id, event, data)

    def get_room_members(self, room_id: str) -> set:
        """Get all members in a room."""
        return self.broadcast_manager.get_room_members(room_id)

    def get_rooms_for_session(self, session_id: str) -> set:
        """Get all rooms for a session."""
        return self.broadcast_manager.get_rooms_for_session(session_id)

    def create_room(self, room_id: str, permission: RoomPermission, owner_id: str, 
                   allowed_users: Set[str] = None, allowed_roles: Set[str] = None) -> Dict[str, Any]:
        """Create a new room with specified permissions."""
        return self.room_manager.create_room(room_id, permission, owner_id, allowed_users, allowed_roles)

    def update_room_permissions(self, room_id: str, permission: RoomPermission = None,
                              allowed_users: Set[str] = None, allowed_roles: Set[str] = None) -> Dict[str, Any]:
        """Update room permissions."""
        return self.room_manager.update_room_permissions(room_id, permission, allowed_users, allowed_roles)

    def get_room_permissions(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get room permissions."""
        return self.room_manager.get_room_permissions(room_id)

    def delete_room(self, room_id: str):
        """Delete a room and its permissions."""
        self.room_manager.delete_room(room_id)