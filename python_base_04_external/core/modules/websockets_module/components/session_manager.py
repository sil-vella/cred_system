from typing import Dict, Any, Optional
from datetime import datetime
from tools.logger.custom_logging import custom_log
from core.managers.redis_manager import RedisManager
from core.managers.jwt_manager import JWTManager, TokenType

class SessionManager:
    def __init__(self, redis_manager: RedisManager, jwt_manager: JWTManager):
        self.redis_manager = redis_manager
        self.jwt_manager = jwt_manager

    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return user data if valid."""
        try:
            # Validate the token - accept both access and websocket tokens
            payload = self.jwt_manager.verify_token(token, TokenType.ACCESS) or \
                     self.jwt_manager.verify_token(token, TokenType.WEBSOCKET)
                     
            if not payload:
                return None
                
            # Get user data from Redis cache using the original key format
            # This matches how user data is stored in connection_api.py
            user_data = self.redis_manager.get(f"user:{payload['id']}")
            if not user_data:
                return None
                
            return user_data
        except Exception as e:
            custom_log(f"Token validation error: {str(e)}")
            return None

    def create_session(self, session_id: str, client_id: str, origin: str, user_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Create a new session with user data."""
        session_data = {
            'client_id': client_id,
            'origin': origin,
            'user_id': user_data['id'],
            'username': user_data['username'],
            'connected_at': datetime.utcnow().isoformat(),
            'last_active': datetime.utcnow().isoformat(),
            'token': token,  # Store token for reconnection validation
            'rooms': []  # Track rooms this session is in
        }
        
        # Store session data in Redis with expiration using secure key
        secure_key = self.redis_manager._generate_secure_key("session", session_id)
        self.redis_manager.set(secure_key, session_data)
        
        custom_log(f"Created new session: {session_id} for user {user_data['id']}")
        return session_data

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis using secure key."""
        secure_key = self.redis_manager._generate_secure_key("session", session_id)
        return self.redis_manager.get(secure_key)

    def update_session(self, session_id: str, session_data: Dict[str, Any]):
        """Update session data in Redis using secure key."""
        secure_key = self.redis_manager._generate_secure_key("session", session_id)
        self.redis_manager.set(secure_key, session_data)

    def delete_session(self, session_id: str):
        """Delete session data from Redis using secure key."""
        secure_key = self.redis_manager._generate_secure_key("session", session_id)
        self.redis_manager.delete(secure_key)
        custom_log(f"Deleted session: {session_id}")

    def add_room_to_session(self, session_id: str, room_id: str):
        """Add a room to a session's room list."""
        session_data = self.get_session(session_id)
        if session_data:
            if 'rooms' not in session_data:
                session_data['rooms'] = []
            elif isinstance(session_data['rooms'], set):
                # Convert set to list if needed
                session_data['rooms'] = list(session_data['rooms'])
                
            if room_id not in session_data['rooms']:
                session_data['rooms'].append(room_id)
            self.update_session(session_id, session_data)

    def remove_room_from_session(self, session_id: str, room_id: str):
        """Remove a room from a session's room list."""
        session_data = self.get_session(session_id)
        if session_data and 'rooms' in session_data:
            if room_id in session_data['rooms']:
                session_data['rooms'].remove(room_id)
                self.update_session(session_id, session_data) 