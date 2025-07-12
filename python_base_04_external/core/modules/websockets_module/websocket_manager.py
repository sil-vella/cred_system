from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request
from typing import Dict, Any, Set, Callable, Optional, List
from tools.logger.custom_logging import custom_log
from core.managers.redis_manager import RedisManager
from core.managers.jwt_manager import JWTManager, TokenType
from core.validators.websocket_validators import WebSocketValidator
from utils.config.config import Config
import time
from datetime import datetime
from functools import wraps
import json

class WebSocketManager:
    def __init__(self):
        self.redis_manager = RedisManager()
        self.validator = WebSocketValidator()
        self.socketio = SocketIO(
            cors_allowed_origins="*",  # Will be overridden by module
            async_mode='threading',
            logger=True,
            engineio_logger=True,
            max_http_buffer_size=Config.WS_MAX_PAYLOAD_SIZE,
            ping_timeout=Config.WS_PING_TIMEOUT,
            ping_interval=Config.WS_PING_INTERVAL
        )
        self.rooms: Dict[str, Set[str]] = {}  # room_id -> set of session_ids
        self.session_rooms: Dict[str, Set[str]] = {}  # session_id -> set of room_ids
        self.rate_limits = {
            'connections': {
                'max': Config.WS_RATE_LIMIT_CONNECTIONS,
                'window': Config.WS_RATE_LIMIT_WINDOW
            },
            'messages': {
                'max': Config.WS_RATE_LIMIT_MESSAGES,
                'window': Config.WS_RATE_LIMIT_WINDOW
            }
        }
        self._jwt_manager = None  # Will be set by the module
        self._room_access_check = None  # Will be set by the module
        self._room_size_limit = Config.WS_ROOM_SIZE_LIMIT
        self._room_size_check_interval = Config.WS_ROOM_SIZE_CHECK_INTERVAL
        self._presence_check_interval = Config.WS_PRESENCE_CHECK_INTERVAL
        self._presence_timeout = Config.WS_PRESENCE_TIMEOUT
        self._presence_cleanup_interval = Config.WS_PRESENCE_CLEANUP_INTERVAL
        custom_log("WebSocketManager initialized")

    def set_cors_origins(self, origins: list):
        """Set allowed CORS origins."""
        self.socketio.cors_allowed_origins = origins
        custom_log(f"Updated CORS origins: {origins}")

    def validate_origin(self, origin: str) -> bool:
        """Validate if the origin is allowed."""
        # Allow all origins if "*" is in the allowed origins
        if "*" in self.socketio.cors_allowed_origins:
            return True
        # Allow mobile app origin
        if origin == "app://mobile":
            return True
        # Check if origin is in the allowed list
        return origin in self.socketio.cors_allowed_origins

    def check_rate_limit(self, client_id: str, limit_type: str) -> bool:
        """Check if client has exceeded rate limits."""
        if limit_type not in self.rate_limits:
            return True  # Unknown limit type, allow by default
            
        limit = self.rate_limits[limit_type]
        key = self.redis_manager._generate_secure_key("rate_limit", limit_type, client_id)
        count = self.redis_manager.get(key) or 0
        
        if count >= limit['max']:
            custom_log(f"Rate limit exceeded for {limit_type}: {client_id}")
            return False
            
        return True

    def update_rate_limit(self, client_id: str, limit_type: str):
        """Update rate limit counter."""
        if limit_type not in self.rate_limits:
            return
            
        limit = self.rate_limits[limit_type]
        key = self.redis_manager._generate_secure_key("rate_limit", limit_type, client_id)
        self.redis_manager.incr(key)
        self.redis_manager.expire(key, limit['window'])

    def store_session_data(self, session_id: str, session_data: Dict[str, Any]):
        """Store session data in Redis."""
        try:
            # Log the incoming data
            custom_log(f"DEBUG - Incoming session data before processing: {session_data}")
            
            # Create a deep copy for storage
            data_to_store = session_data.copy()
            
            # Convert any sets to lists for JSON serialization
            if 'rooms' in data_to_store:
                if isinstance(data_to_store['rooms'], set):
                    data_to_store['rooms'] = list(data_to_store['rooms'])
                    custom_log(f"DEBUG - Converted rooms from set to list: {data_to_store['rooms']}")
                elif not isinstance(data_to_store['rooms'], list):
                    data_to_store['rooms'] = []
                    custom_log("DEBUG - Initialized rooms as empty list")
            
            if 'user_roles' in data_to_store:
                if isinstance(data_to_store['user_roles'], set):
                    data_to_store['user_roles'] = list(data_to_store['user_roles'])
                    custom_log(f"DEBUG - Converted user_roles from set to list: {data_to_store['user_roles']}")
                elif not isinstance(data_to_store['user_roles'], list):
                    data_to_store['user_roles'] = []
                    custom_log("DEBUG - Initialized user_roles as empty list")
            
            # Convert any integers to strings
            if 'user_id' in data_to_store and isinstance(data_to_store['user_id'], int):
                data_to_store['user_id'] = str(data_to_store['user_id'])
                custom_log(f"DEBUG - Converted user_id to string: {data_to_store['user_id']}")
            
            # Handle any nested structures
            for key, value in data_to_store.items():
                if isinstance(value, (set, datetime)):
                    data_to_store[key] = str(value)
                    custom_log(f"DEBUG - Converted {key} from {type(value)} to string: {data_to_store[key]}")
                elif isinstance(value, (int, float)):
                    data_to_store[key] = str(value)
                    custom_log(f"DEBUG - Converted {key} from {type(value)} to string: {data_to_store[key]}")
                elif isinstance(value, list):
                    # Convert any sets within lists to lists
                    data_to_store[key] = [
                        list(item) if isinstance(item, set) else 
                        str(item) if isinstance(item, (datetime, int, float)) else 
                        item 
                        for item in value
                    ]
                    custom_log(f"DEBUG - Processed list in {key}: {data_to_store[key]}")
                elif isinstance(value, dict):
                    # Handle nested dictionaries
                    data_to_store[key] = {
                        k: (list(v) if isinstance(v, set) else 
                            str(v) if isinstance(v, (datetime, int, float)) else 
                            v)
                        for k, v in value.items()
                    }
                    custom_log(f"DEBUG - Processed dict in {key}: {data_to_store[key]}")
            
            # Store in Redis with expiration
            session_key = self.redis_manager._generate_secure_key("session", session_id)
            self.redis_manager.set(session_key, data_to_store, expire=Config.WS_SESSION_TTL)
            custom_log(f"DEBUG - Final data stored for session {session_id}: {data_to_store}")
            
        except Exception as e:
            custom_log(f"Error storing session data: {str(e)}")
            raise

    def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        try:
            session_key = self.redis_manager._generate_secure_key("session", session_id)
            data = self.redis_manager.get(session_key)
            if data:
                # Create a deep copy to avoid modifying the original data
                data_copy = data.copy()
                
                # Convert lists back to sets for internal use
                if 'rooms' in data_copy:
                    data_copy['rooms'] = set(data_copy['rooms'])
                if 'user_roles' in data_copy:
                    data_copy['user_roles'] = set(data_copy['user_roles'])
                
                # Handle any nested sets in the data
                for key, value in data_copy.items():
                    if isinstance(value, list):
                        # Check if this list should be a set
                        if key in ['rooms', 'user_roles']:
                            data_copy[key] = set(value)
                        else:
                            # Check for nested sets in the list
                            data_copy[key] = [
                                set(item) if isinstance(item, list) and key in ['rooms', 'user_roles'] else
                                item
                                for item in value
                            ]
                    elif isinstance(value, dict):
                        # Handle nested dictionaries
                        for k, v in value.items():
                            if isinstance(v, list) and k in ['rooms', 'user_roles']:
                                value[k] = set(v)
                            elif isinstance(v, list):
                                # Check for nested sets in the list
                                value[k] = [
                                    set(item) if isinstance(item, list) and k in ['rooms', 'user_roles'] else
                                    item
                                    for item in v
                                ]
                
                # Create a copy for client use with lists instead of sets
                client_data = data_copy.copy()
                
                # Convert sets to lists for client use
                if 'rooms' in client_data and isinstance(client_data['rooms'], set):
                    client_data['rooms'] = list(client_data['rooms'])
                if 'user_roles' in client_data and isinstance(client_data['user_roles'], set):
                    client_data['user_roles'] = list(client_data['user_roles'])
                
                # Handle any nested sets in the client data
                for key, value in client_data.items():
                    if isinstance(value, list):
                        # Check for nested sets in the list
                        client_data[key] = [
                            list(item) if isinstance(item, set) else
                            item
                            for item in value
                        ]
                    elif isinstance(value, dict):
                        # Handle nested dictionaries
                        for k, v in value.items():
                            if isinstance(v, set):
                                value[k] = list(v)
                            elif isinstance(v, list):
                                # Check for nested sets in the list
                                value[k] = [
                                    list(item) if isinstance(item, set) else
                                    item
                                    for item in v
                                ]
                
                # Store the client-safe version in the data
                data_copy['_client_data'] = client_data
                
                return data_copy
            return None
        except Exception as e:
            custom_log(f"Error getting session data: {str(e)}")
            return None

    def get_client_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data in a format safe for client transmission."""
        try:
            data = self.get_session_data(session_id)
            if data and '_client_data' in data:
                return data['_client_data']
            return None
        except Exception as e:
            custom_log(f"Error getting client session data: {str(e)}")
            return None

    def cleanup_session_data(self, session_id: str):
        """Clean up session data from Redis."""
        session_key = self.redis_manager._generate_secure_key("session", session_id)
        self.redis_manager.delete(session_key)

    def update_session_activity(self, session_id: str):
        """Update last active timestamp for session."""
        try:
            session_key = self.redis_manager._generate_secure_key("session", session_id)
            session_data = self.redis_manager.get(session_key)
            if session_data:
                session_data['last_active'] = datetime.utcnow().isoformat()
                # Convert sets to lists before storing
                if 'rooms' in session_data and isinstance(session_data['rooms'], set):
                    session_data['rooms'] = list(session_data['rooms'])
                if 'user_roles' in session_data and isinstance(session_data['user_roles'], set):
                    session_data['user_roles'] = list(session_data['user_roles'])
                self.redis_manager.set(session_key, session_data)
                custom_log(f"Updated session activity for {session_id}")
        except Exception as e:
            custom_log(f"Error updating session activity: {str(e)}")

    def initialize(self, app, use_builtin_handlers=True):
        """Initialize the WebSocket manager with a Flask app."""
        # Initialize socketio with the Flask app
        self.socketio.init_app(app, cors_allowed_origins="*")
        custom_log("WebSocket manager initialized with Flask app")
        
        # Register a catch-all handler for debugging
        @self.socketio.on('*')
        def catch_all(event, data=None):
            custom_log(f"Catch-all handler received event: {event} with data: {data}")
            return None
            
        # Register a debug handler for join_game event
        @self.socketio.on('join_game')
        def debug_join_game(data=None):
            custom_log(f"Debug handler received join_game event with data: {data}")
            return None

        try:
            custom_log("Starting WebSocket initialization...")
            self.socketio.init_app(app, cors_allowed_origins="*")
            
            # Only set up built-in handlers if requested
            custom_log(f"DEBUG - use_builtin_handlers: {use_builtin_handlers}")
            if use_builtin_handlers:
                @self.socketio.on('connect')
                def handle_connect():
                    try:
                        session_id = request.sid
                        custom_log(f"New WebSocket connection attempt from session {session_id}")
                        custom_log(f"Connection headers: {dict(request.headers)}")
                        custom_log(f"Connection args: {dict(request.args)}")
                        
                        # Get token from request
                        token = request.args.get('token')
                        if not token:
                            custom_log(f"No token provided for WebSocket connection from session {session_id}")
                            return False
                            
                        # Validate token with JWT manager
                        if not self._jwt_manager:
                            custom_log(f"JWT manager not initialized for session {session_id}")
                            return False
                            
                        # Verify token and get payload - accept both access and websocket tokens
                        custom_log(f"Verifying token for session {session_id}")
                        payload = self._jwt_manager.verify_token(token, TokenType.ACCESS) or \
                                 self._jwt_manager.verify_token(token, TokenType.WEBSOCKET)
                                 
                        if not payload:
                            custom_log(f"Invalid token for WebSocket connection from session {session_id}")
                            return False
                            
                        custom_log(f"Token verified for session {session_id}, payload: {payload}")
                            
                        # Store session data
                        session_data = {
                            'user_id': str(payload.get('id')),  # Convert to string immediately
                            'username': payload.get('username'),
                            'token': token,
                            'token_type': payload.get('type'),
                            'connected_at': datetime.utcnow().isoformat(),
                            'last_active': datetime.utcnow().isoformat(),
                            'rooms': [],  # Initialize as empty list
                            'client_id': request.headers.get('X-Client-ID', session_id),
                            'origin': request.headers.get('Origin', '')
                        }
                        
                        # Convert any sets to lists for JSON serialization
                        if 'user_roles' in payload:
                            if isinstance(payload['user_roles'], set):
                                session_data['user_roles'] = list(payload['user_roles'])
                            else:
                                session_data['user_roles'] = list(payload['user_roles']) if payload['user_roles'] else []
                        else:
                            session_data['user_roles'] = []
                        
                        # Log the session data before storage
                        custom_log(f"DEBUG - Session data before storage: {session_data}")
                        
                        # Store session data in Redis with expiration
                        self.store_session_data(session_id, session_data)
                        
                        # Update session activity
                        self.update_session_activity(session_id)
                        
                        # Mark user as online
                        if session_data.get('user_id'):
                            custom_log(f"Marking user {session_data['user_id']} as online")
                            self.update_user_presence(session_data['user_id'], 'online')
                        
                        # Create a client-safe version of the data
                        client_data = {}
                        for key, value in session_data.items():
                            if key == '_client_data':  # Skip the _client_data field itself
                                continue
                            if isinstance(value, (set, datetime)):
                                client_data[key] = str(value)
                            elif isinstance(value, (int, float)):
                                client_data[key] = str(value)
                            elif isinstance(value, list):
                                client_data[key] = [
                                    list(item) if isinstance(item, set) else 
                                    str(item) if isinstance(item, (datetime, int, float)) else 
                                    item 
                                    for item in value
                                ]
                            elif isinstance(value, dict):
                                client_data[key] = {
                                    k: (list(v) if isinstance(v, set) else 
                                        str(v) if isinstance(v, (datetime, int, float)) else 
                                        v)
                                    for k, v in value.items()
                                }
                            else:
                                client_data[key] = value
                        
                        # Store the client-safe version in the session data
                        session_data['_client_data'] = client_data
                        
                        # Verify JSON serialization before emitting
                        try:
                            import json
                            json.dumps(client_data)
                            custom_log("DEBUG - Successfully verified client data JSON serialization")
                        except Exception as e:
                            custom_log(f"DEBUG - Client data JSON serialization failed: {str(e)}")
                            # If serialization still fails, convert all non-string values to strings
                            for key, value in client_data.items():
                                if not isinstance(value, str):
                                    client_data[key] = str(value)
                        
                        # Send session data to client
                        custom_log(f"DEBUG - Sending session data to client {session_id}: {client_data}")
                        self.socketio.emit('session_data', client_data, room=session_id)
                        
                        custom_log(f"WebSocket connection established for session {session_id}")
                        return True
                        
                    except Exception as e:
                        custom_log(f"Error in connect handler for session {request.sid}: {str(e)}")
                        return False

                @self.socketio.on('disconnect')
                def handle_disconnect():
                    try:
                        session_id = request.sid
                        custom_log(f"WebSocket disconnection for session {session_id}")
                        
                        # Get session data before cleanup
                        session_data = self.get_session_data(session_id)
                        if session_data:
                            custom_log(f"Found session data for {session_id}: {session_data}")
                            
                            # Revoke the token if it exists
                            token = session_data.get('token')
                            if token and self._jwt_manager:
                                custom_log(f"Revoking token for session {session_id}")
                                self._jwt_manager.revoke_token(token)
                            
                            # Leave all rooms
                            for room_id in session_data.get('rooms', set()):
                                custom_log(f"Leaving room {room_id} for session {session_id}")
                                self.leave_room(room_id, session_id)
                                
                            # Mark user as offline
                            if session_data.get('user_id'):
                                custom_log(f"Marking user {session_data['user_id']} as offline")
                                self.update_user_presence(session_data['user_id'], 'offline')
                        else:
                            custom_log(f"No session data found for {session_id} during disconnect")
                        
                        # Clean up session data
                        custom_log(f"Cleaning up session data for {session_id}")
                        self.cleanup_session_data(session_id)
                        
                        # Clean up rate limit data
                        if session_data and session_data.get('client_id'):
                            custom_log(f"Cleaning up rate limit data for client {session_data['client_id']}")
                            for limit_type in self.rate_limits:
                                key = self.redis_manager._generate_secure_key("rate_limit", limit_type, session_data['client_id'])
                                self.redis_manager.delete(key)
                        
                    except Exception as e:
                        custom_log(f"Error in disconnect handler for session {request.sid}: {str(e)}")

                @self.socketio.on('join')
                def handle_join(data=None):
                    try:
                        session_id = request.sid
                        custom_log(f"Join request received for session {session_id}: {data}")
                        
                        # Get session data
                        session_data = self.get_session_data(session_id)
                        if not session_data:
                            custom_log(f"No session data found for join request from session {session_id}")
                            self.socketio.emit('error', {'message': 'Session not found'}, room=session_id)
                            return
                            
                        # Convert any sets in session data to lists
                        if 'rooms' in session_data and isinstance(session_data['rooms'], set):
                            session_data['rooms'] = list(session_data['rooms'])
                        if 'user_roles' in session_data and isinstance(session_data['user_roles'], set):
                            session_data['user_roles'] = list(session_data['user_roles'])
                            
                        custom_log(f"Attempting to join room {data['room_id']} for session {session_id}")
                        
                        # Join room
                        if self.join_room(data['room_id'], session_id):
                            custom_log(f"Successfully joined room {data['room_id']} for session {session_id}")
                            self.socketio.emit('join_response', {
                                'success': True,
                                'room_id': data['room_id'],
                                'message': 'Successfully joined room'
                            }, room=session_id)
                        else:
                            custom_log(f"Failed to join room {data['room_id']} for session {session_id}")
                            self.socketio.emit('join_response', {
                                'success': False,
                                'room_id': data['room_id'],
                                'message': 'Failed to join room'
                            }, room=session_id)
                            
                    except Exception as e:
                        custom_log(f"Error in join handler for session {request.sid}: {str(e)}")
                        self.socketio.emit('error', {'message': str(e)}, room=request.sid)

                custom_log("WebSocket support initialized with Flask app")
        except Exception as e:
            custom_log(f"Error initializing WebSocket support: {str(e)}")

    def set_jwt_manager(self, jwt_manager):
        """Set the JWT manager instance."""
        self._jwt_manager = jwt_manager
        custom_log("JWT manager set in WebSocketManager")

    def set_room_access_check(self, access_check_func):
        """Set the room access check function."""
        self._room_access_check = access_check_func
        custom_log("Room access check function set")

    def _update_room_permissions(self, room_id: str, room_data: Dict[str, Any], session_id: Optional[str] = None):
        """Update room permissions."""
        try:
            custom_log(f"Updating permissions for room {room_id}")
            
            # Convert any sets to lists for JSON serialization
            if 'allowed_users' in room_data and isinstance(room_data['allowed_users'], set):
                room_data['allowed_users'] = list(room_data['allowed_users'])
            if 'allowed_roles' in room_data and isinstance(room_data['allowed_roles'], set):
                room_data['allowed_roles'] = list(room_data['allowed_roles'])
                
            # Convert any integers to strings for Redis storage
            if 'owner_id' in room_data and isinstance(room_data['owner_id'], int):
                room_data['owner_id'] = str(room_data['owner_id'])
            if 'size' in room_data and isinstance(room_data['size'], int):
                room_data['size'] = str(room_data['size'])
            
            # Store room permissions
            permissions_key = self.redis_manager._generate_secure_key("room_permissions", room_id)
            self.redis_manager.set(permissions_key, room_data)
            custom_log(f"Updated permissions for room {room_id}: {room_data}")
            
            # If session_id is provided, update session data
            if session_id:
                session_data = self.get_session_data(session_id)
                if session_data:
                    # Ensure rooms is a set for internal use
                    if 'rooms' not in session_data:
                        session_data['rooms'] = set()
                    elif not isinstance(session_data['rooms'], set):
                        session_data['rooms'] = set(session_data['rooms'])
                    
                    # Add the room to the set
                    session_data['rooms'].add(room_id)
                    
                    # Create a copy for Redis storage with lists instead of sets
                    data_to_store = session_data.copy()
                    if 'rooms' in data_to_store and isinstance(data_to_store['rooms'], set):
                        data_to_store['rooms'] = list(data_to_store['rooms'])
                    if 'user_roles' in data_to_store and isinstance(data_to_store['user_roles'], set):
                        data_to_store['user_roles'] = list(data_to_store['user_roles'])
                    
                    # Store the serializable version in Redis
                    session_key = self.redis_manager._generate_secure_key("session", session_id)
                    self.redis_manager.set(session_key, data_to_store, expire=Config.WS_SESSION_TTL)
                    custom_log(f"Updated session {session_id} with room {room_id}")
            
        except Exception as e:
            custom_log(f"Error updating room permissions: {str(e)}")

    def check_room_access(self, room_id: str, user_id: str, user_roles: List[str], session_id: Optional[str] = None) -> bool:
        """Check if user has access to room"""
        try:
            custom_log(f"Checking room access for user {user_id} in room {room_id}")
            
            # Get room permissions from Redis
            permissions_key = self.redis_manager._generate_secure_key("room_permissions", room_id)
            room_permissions = self.redis_manager.get(permissions_key)
            if not room_permissions:
                # Room doesn't exist, return False
                custom_log(f"Room {room_id} doesn't exist")
                return False

            # Convert sets to lists for logging
            log_permissions = room_permissions.copy()
            if 'allowed_users' in log_permissions and isinstance(log_permissions['allowed_users'], set):
                log_permissions['allowed_users'] = list(log_permissions['allowed_users'])
            if 'allowed_roles' in log_permissions and isinstance(log_permissions['allowed_roles'], set):
                log_permissions['allowed_roles'] = list(log_permissions['allowed_roles'])

            custom_log(f"DEBUG - Room permissions found: {log_permissions}")

            # Parse room permissions
            permission_type = room_permissions.get("permission", "public")
            allowed_users = set(room_permissions.get("allowed_users", []))
            allowed_roles = set(room_permissions.get("allowed_roles", []))
            
            custom_log(f"Room {room_id} permission type: {permission_type}")
            custom_log(f"Allowed users: {list(allowed_users)}")
            custom_log(f"Allowed roles: {list(allowed_roles)}")
            custom_log(f"User roles: {user_roles}")

            # Check access based on permission type
            if permission_type == "public":
                custom_log(f"Public room access granted for user {user_id}")
                return True
            elif permission_type == "private":
                has_access = user_id in allowed_users
                custom_log(f"Private room access {'granted' if has_access else 'denied'} for user {user_id}")
                return has_access
            elif permission_type == "restricted":
                has_access = (user_id in allowed_users or 
                            any(role in allowed_roles for role in user_roles))
                custom_log(f"Restricted room access {'granted' if has_access else 'denied'} for user {user_id}")
                return has_access
            elif permission_type == "owner_only":
                has_access = user_id == room_permissions.get("owner_id")
                custom_log(f"Owner-only room access {'granted' if has_access else 'denied'} for user {user_id}")
                return has_access
            else:
                custom_log(f"Invalid permission type: {permission_type}")
            return False
            
        except Exception as e:
            custom_log(f"Error checking room access: {str(e)}")
            return False

    def requires_auth(self, handler: Callable) -> Callable:
        """Decorator to require authentication for WebSocket handlers."""
        @wraps(handler)
        def wrapper(data=None):
            try:
                session_id = request.sid
                
                # Get session data
                session_data = self.get_session_data(session_id)
                if not session_data or 'user_id' not in session_data:
                    custom_log(f"Session {session_id} not authenticated")
                    return {'status': 'error', 'message': 'Authentication required'}
                
                # Update session activity
                self.update_session_activity(session_id)
                
                # Call the handler with session data
                return handler(data, session_data)
            except Exception as e:
                custom_log(f"Error in authenticated handler: {str(e)}")
                return {'status': 'error', 'message': str(e)}
        return wrapper

    def register_handler(self, event: str, handler: Callable):
        """Register a WebSocket event handler without authentication."""
        @self.socketio.on(event)
        def wrapped_handler(data=None):
            try:
                # Skip validation for special events
                if event in ['connect', 'disconnect']:
                    # For connect event, ensure we're not passing any data that might contain sets
                    if event == 'connect':
                        return handler()
                    return handler(data)
                    
                # Ensure data is a dictionary if None is provided
                if data is None:
                    data = {}
                    
                # Validate event payload
                error = self.validator.validate_event_payload(event, data)
                if error:
                    custom_log(f"Validation error in {event} handler: {error}")
                    return {'status': 'error', 'message': str(error)}
                    
                # Validate message size based on event type
                if event == 'message':
                    error = self.validator.validate_message(data)
                elif event == 'binary':
                    error = self.validator.validate_binary_data(data)
                else:
                    error = self.validator.validate_json_data(data)
                    
                if error:
                    custom_log(f"Message size validation error in {event} handler: {error}")
                    return {'status': 'error', 'message': str(error)}
                    
                # Ensure data is JSON serializable
                serializable_data = {}
                for key, value in data.items():
                    if isinstance(value, (set, datetime)):
                        serializable_data[key] = str(value)
                    elif isinstance(value, (int, float)):
                        serializable_data[key] = str(value)
                    else:
                        serializable_data[key] = value
                        
                return handler(serializable_data)
            except Exception as e:
                custom_log(f"Error in {event} handler: {str(e)}")
                return {'status': 'error', 'message': str(e)}

    def register_authenticated_handler(self, event: str, handler: Callable):
        """Register a WebSocket event handler with authentication."""
        custom_log(f"DEBUG - Registering authenticated handler for event: {event}")
        
        @self.socketio.on(event)
        def wrapped_handler(data=None):
            custom_log(f"DEBUG - Received event: {event} with data: {data}")
            try:
                # Skip validation for special events
                if event in ['connect', 'disconnect']:
                    custom_log(f"DEBUG - Skipping validation for special event: {event}")
                    return handler(data)
                    
                # Get session ID
                session_id = request.sid
                if not session_id:
                    custom_log(f"ERROR - No session ID found for event: {event}")
                    return {'status': 'error', 'message': 'No session ID'}
                custom_log(f"DEBUG - Processing event {event} for session: {session_id}")
                    
                # Call handler with session ID and data
                try:
                    custom_log(f"DEBUG - Calling handler with session_id and data")
                    result = handler(session_id, data or {})
                    custom_log(f"DEBUG - Handler returned: {result}")
                    
                    # Check if result is a coroutine
                    if hasattr(result, '__await__'):
                        custom_log(f"DEBUG - Handler returned a coroutine, awaiting it")
                        import asyncio
                        try:
                            # Try to get the current event loop
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            # If no event loop exists, create a new one
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            
                        try:
                            result = loop.run_until_complete(result)
                            custom_log(f"DEBUG - Coroutine completed with result: {result}")
                            return result
                        except Exception as e:
                            custom_log(f"ERROR - Error awaiting coroutine: {str(e)}")
                            return {'status': 'error', 'message': str(e)}
                    
                    return result
                except TypeError as e:
                    # If handler doesn't accept session_id, call with just data
                    custom_log(f"WARNING - Handler doesn't accept session_id, calling with just data: {e}")
                    try:
                        result = handler(data or {})
                        if hasattr(result, '__await__'):
                            custom_log(f"DEBUG - Handler returned a coroutine, awaiting it")
                            import asyncio
                            try:
                                loop = asyncio.get_event_loop()
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                            try:
                                result = loop.run_until_complete(result)
                                return result
                            except Exception as e:
                                custom_log(f"ERROR - Error awaiting coroutine: {str(e)}")
                                return {'status': 'error', 'message': str(e)}
                        return result
                    except Exception as e:
                        custom_log(f"ERROR - Error in handler: {str(e)}")
                        return {'status': 'error', 'message': str(e)}
                    
            except Exception as e:
                custom_log(f"CRITICAL ERROR - Error in {event} handler: {str(e)}")
                return {'status': 'error', 'message': str(e)}

    def create_room(self, room_id: str, permission: str = "public", 
                   owner_id: Optional[int] = None,
                   allowed_users: Optional[Set[int]] = None,
                   allowed_roles: Optional[Set[str]] = None) -> bool:
        """Create a new room with specified permissions"""
        try:
            # Initialize room data
            room_data = {
                "permission": permission,
                "owner_id": str(owner_id) if owner_id is not None else None,
                "allowed_users": list(allowed_users) if allowed_users else [],
                "allowed_roles": list(allowed_roles) if allowed_roles else [],
                "created_at": datetime.utcnow().isoformat(),
                "size": "0"
            }

            # Store room permissions
            self._update_room_permissions(room_id, room_data)

            # Initialize room size
            size_key = self.redis_manager._generate_secure_key("room_size", room_id)
            self.redis_manager.set(size_key, "0")

            custom_log(f"Created room {room_id} with {permission} permission")
            return True

        except Exception as e:
            custom_log(f"Error creating room: {str(e)}")
        return False

    def get_room_size(self, room_id: str) -> int:
        """Get the current number of users in a room."""
        size_key = self.redis_manager._generate_secure_key("room_size", room_id)
        return int(self.redis_manager.get(size_key) or "0")

    def update_room_size(self, room_id: str, delta: int):
        """Update the room size in Redis."""
        size_key = self.redis_manager._generate_secure_key("room_size", room_id)
        self.redis_manager.update_room_size(size_key, delta)

    def check_room_size_limit(self, room_id: str) -> bool:
        """Check if a room has reached its size limit."""
        current_size = self.get_room_size(room_id)
        return current_size >= self._room_size_limit

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session information."""
        return self.get_session_data(session_id)

    def update_user_presence(self, session_id: str, status: str = 'online'):
        """Update user presence status."""
        try:
            custom_log(f"Updating presence for session {session_id} to status: {status}")
            session_info = self.get_session_info(session_id)
            if not session_info or 'user_id' not in session_info:
                custom_log(f"No valid session info found for session {session_id}")
                return
                
            user_id = session_info['user_id']
            presence_key = self.redis_manager._generate_secure_key("presence", user_id)
            
            presence_data = {
                'status': status,
                'last_seen': datetime.utcnow().isoformat(),
                'session_id': session_id,
                'username': session_info.get('username', 'Anonymous')
            }
            
            custom_log(f"Setting presence data for user {user_id}: {presence_data}")
            self.redis_manager.set(presence_key, presence_data, expire=self._presence_timeout)
            
            # Broadcast presence update to all rooms the user is in
            rooms = self.get_rooms_for_session(session_id)
            custom_log(f"Broadcasting presence update to rooms: {rooms}")
            for room_id in rooms:
                self.broadcast_to_room(room_id, 'presence_update', {
                    'user_id': user_id,
                    'status': status,
                    'username': presence_data['username']
                })
                
        except Exception as e:
            custom_log(f"Error updating presence for session {session_id}: {str(e)}")

    def get_user_presence(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user presence information."""
        try:
            custom_log(f"Getting presence for user {user_id}")
            presence_key = self.redis_manager._generate_secure_key("presence", user_id)
            presence_data = self.redis_manager.get(presence_key)
            
            if not presence_data:
                custom_log(f"No presence data found for user {user_id}")
                return {
                    'user_id': user_id,
                    'status': 'offline',
                    'last_seen': None
                }
                
            # Check if presence is stale
            last_seen = datetime.fromisoformat(presence_data['last_seen'])
            if (datetime.utcnow() - last_seen).total_seconds() > self._presence_timeout:
                custom_log(f"Presence data for user {user_id} is stale, marking as offline")
                presence_data['status'] = 'offline'
                
            custom_log(f"Retrieved presence data for user {user_id}: {presence_data}")
            return presence_data
            
        except Exception as e:
            custom_log(f"Error getting presence for user {user_id}: {str(e)}")
            return None

    def get_room_presence(self, room_id: str) -> List[Dict[str, Any]]:
        """Get presence information for all users in a room."""
        try:
            custom_log(f"Getting presence for room {room_id}")
            room_members = self.get_room_members(room_id)
            presence_list = []
            
            for session_id in room_members:
                session_info = self.get_session_info(session_id)
                if session_info and 'user_id' in session_info:
                    presence_data = self.get_user_presence(session_info['user_id'])
                    if presence_data:
                        presence_list.append(presence_data)
                        
            custom_log(f"Room {room_id} presence list: {presence_list}")
            return presence_list
            
        except Exception as e:
            custom_log(f"Error getting room presence for {room_id}: {str(e)}")
            return []

    def cleanup_stale_presence(self):
        """Clean up stale presence records."""
        try:
            custom_log("Starting stale presence cleanup")
            # This would be called periodically to clean up stale presence records
            # Implementation would depend on Redis key pattern matching capabilities
            custom_log("Completed stale presence cleanup")
            
        except Exception as e:
            custom_log(f"Error cleaning up stale presence: {str(e)}")

    def _join_room_internal(self, room_id: str, session_id: str, user_id: Optional[str] = None, user_roles: Optional[Set[str]] = None) -> bool:
        """Internal method to handle room joining logic."""
        try:
            custom_log(f"DEBUG - Starting join_room process for room {room_id} and session {session_id}")
            
            # Validate room ID
            if not room_id:
                custom_log("ERROR - Invalid room ID provided")
                self.socketio.emit('error', {'message': 'Invalid room ID'}, room=session_id)
                return False
                
            # Get session data
            custom_log(f"DEBUG - Attempting to get session data for {session_id}")
            session_data = self.get_session_data(session_id)
            if not session_data:
                custom_log(f"ERROR - No session data found for {session_id}")
                self.socketio.emit('error', {'message': 'Session not found'}, room=session_id)
                return False
            custom_log(f"DEBUG - Session data retrieved: {session_data}")
                
            # Check if room exists first - this must be the first check after session validation
            custom_log(f"DEBUG - Checking if room {room_id} exists")
            permissions_key = self.redis_manager._generate_secure_key("room_permissions", room_id)
            room_permissions = self.redis_manager.get(permissions_key)
            if not room_permissions:
                custom_log(f"ERROR - Room {room_id} does not exist in Redis")
                self.socketio.emit('error', {'message': 'Room does not exist'}, room=session_id)
                return False
            custom_log(f"DEBUG - Room permissions found: {room_permissions}")
                
            # Update session data with user_id and roles if provided
            if user_id:
                custom_log(f"DEBUG - Updating session with user_id: {user_id}")
                session_data['user_id'] = user_id
            if user_roles:
                custom_log(f"DEBUG - Updating session with roles: {user_roles}")
                session_data['user_roles'] = list(user_roles)  # Convert set to list for JSON serialization
                
            # Check room access
            custom_log(f"DEBUG - Checking room access for user {session_data.get('user_id')}")
            if not self.check_room_access(room_id, session_data['user_id'], session_data.get('user_roles', []), session_id):
                custom_log(f"ERROR - Access denied to room {room_id} for session {session_id}")
                self.socketio.emit('error', {'message': 'Access denied to room'}, room=session_id)
                return False
            custom_log("DEBUG - Room access granted")
                
            # Check current room size
            custom_log(f"DEBUG - Checking room size for {room_id}")
            size_key = self.redis_manager._generate_secure_key("room_size", room_id)
            current_size = int(self.redis_manager.get(size_key) or "0")
            if current_size >= self._room_size_limit:
                custom_log(f"ERROR - Room {room_id} has reached size limit of {self._room_size_limit}")
                self.socketio.emit('room_full', {
                    'room_id': room_id,
                    'current_size': current_size,
                    'max_size': self._room_size_limit
                }, room=session_id)
                return False
            custom_log(f"DEBUG - Room size check passed: {current_size}/{self._room_size_limit}")
                
            # Try to increment room size atomically
            new_size = current_size + 1
            self.redis_manager.set(size_key, str(new_size))
            custom_log(f"DEBUG - Room size updated to {new_size}")
                
            # Join the room
            custom_log(f"DEBUG - Attempting to join room {room_id}")
            self.socketio.emit('room_joined', {
                'room_id': room_id,
                'current_size': new_size,
                'max_size': self._room_size_limit
            }, room=session_id)
            join_room(room_id, sid=session_id)  # Use the imported join_room function
            custom_log(f"DEBUG - Successfully joined room {room_id}")
            
            # Update room memberships
            custom_log("DEBUG - Updating room memberships")
            if room_id not in self.rooms:
                self.rooms[room_id] = set()
            self.rooms[room_id].add(session_id)
            
            if session_id not in self.session_rooms:
                self.session_rooms[session_id] = set()
            self.session_rooms[session_id].add(room_id)
            
            # Ensure rooms is a set for internal use
            if 'rooms' not in session_data:
                session_data['rooms'] = set()
            elif not isinstance(session_data['rooms'], set):
                session_data['rooms'] = set(session_data['rooms'])
            
            # Add the room to the set
            session_data['rooms'].add(room_id)
            
            # Create a copy for Redis storage with lists instead of sets
            data_to_store = session_data.copy()
            if 'rooms' in data_to_store and isinstance(data_to_store['rooms'], set):
                data_to_store['rooms'] = list(data_to_store['rooms'])
            if 'user_roles' in data_to_store and isinstance(data_to_store['user_roles'], set):
                data_to_store['user_roles'] = list(data_to_store['user_roles'])
            
            # Store the serializable version in Redis
            custom_log(f"DEBUG - Storing updated session data: {data_to_store}")
            session_key = self.redis_manager._generate_secure_key("session", session_id)
            self.redis_manager.set(session_key, data_to_store, expire=Config.WS_SESSION_TTL)
            
            # Broadcast user joined event if user_id is present
            if user_id:
                custom_log(f"DEBUG - Broadcasting user_joined event for user {user_id}")
                self.socketio.emit('user_joined', {
                    'user_id': user_id,
                    'username': session_data.get('username'),
                    'roles': list(user_roles) if user_roles else [],
                    'current_size': new_size,
                    'max_size': self._room_size_limit
                }, room=room_id)
                
            custom_log(f"SUCCESS - Session {session_id} joined room {room_id}")
            return True
            
        except Exception as e:
            custom_log(f"CRITICAL ERROR - Error joining room {room_id} for session {session_id}: {str(e)}")
            self.socketio.emit('error', {'message': 'Failed to join room'}, room=session_id)
            return False

    def join_room(self, room_id: str, session_id: str, user_id: Optional[str] = None, user_roles: Optional[Set[str]] = None) -> bool:
        """Join a room with proper validation and room size tracking."""
        return self._join_room_internal(room_id, session_id, user_id, user_roles)

    def leave_room(self, room_id: str, session_id: str):
        """Leave a room and update room size."""
        try:
            custom_log(f"Starting room leave process for session {session_id} from room {room_id}")
            
            # Get session info before any cleanup
            session_info = self.get_session_info(session_id)
            if not session_info:
                custom_log(f"No session info found for {session_id} during room leave")
                return False
                
            user_id = session_info.get('user_id')
            username = session_info.get('username', 'Anonymous')
            
            # Update room tracking first
            if room_id in self.rooms:
                self.rooms[room_id].discard(session_id)
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
                    
            if session_id in self.session_rooms:
                self.session_rooms[session_id].discard(room_id)
                if not self.session_rooms[session_id]:
                    del self.session_rooms[session_id]
                    
            # Update user presence
            self.update_user_presence(session_id, 'away')
            
            # Broadcast presence update to room
            self.broadcast_to_room(room_id, 'user_left', {
                'user_id': user_id,
                'username': username
            })
            
            # Leave the room last
            leave_room(room_id, sid=session_id)
            
            # Update room size in Redis
            size_key = self.redis_manager._generate_secure_key("room_size", room_id)
            self.redis_manager.update_room_size(size_key, -1)
            
            custom_log(f"Session {session_id} successfully left room {room_id}")
            return True
            
        except Exception as e:
            custom_log(f"Error during room leave for session {session_id}: {str(e)}")
            return False

    async def broadcast_to_room(self, room_id: str, event: str, data: Any):
        """Broadcast message to a specific room."""
        if not room_id:
            custom_log("Cannot broadcast to empty room_id", level="error")
            return
            
        if not isinstance(data, (dict, list, str, int, float, bool, type(None))):
            custom_log(f"Invalid data type for broadcast: {type(data)}", level="error")
            return
            
        room_members = self.get_room_members(room_id)
        for session_id in room_members:
            await self.send_to_session(session_id, event, data)
            
    async def send_to_session(self, session_id: str, event: str, data: Any):
        """Send message to a specific session."""
        if not session_id:
            custom_log("Cannot send to empty session_id", level="error")
            return
            
        if not isinstance(data, (dict, list, str, int, float, bool, type(None))):
            custom_log(f"Invalid data type for send: {type(data)}", level="error")
            return
            
        session = self.get_session_info(session_id)
        if session and session.websocket:
            try:
                await session.websocket.send_json({
                    "event": event,
                    "data": data
                })
            except Exception as e:
                custom_log(f"Error sending to session {session_id}: {str(e)}", level="error")

    def broadcast_to_all(self, event: str, data: Dict[str, Any]):
        """Broadcast an event to all connected clients."""
        # Validate event payload
        error = self.validator.validate_event_payload(event, data)
        if error:
            custom_log(f"Validation error in broadcast: {error}")
            return False
            
        emit(event, data)
        return True

    def send_to_session(self, session_id: str, event: str, data: Any):
        """Send message to a specific client."""
        emit(event, data, room=session_id)

    def get_room_members(self, room_id: str) -> set:
        """Get all session IDs in a room."""
        return self.rooms.get(room_id, set())

    def get_rooms_for_session(self, session_id: str) -> set:
        """Get all rooms a session is in."""
        return self.session_rooms.get(session_id, set())

    def reset_room_sizes(self):
        """Reset all room sizes in Redis to match actual connected users."""
        try:
            custom_log("Starting room size reset")
            
            # Log current state
            custom_log(f"Current rooms state: {self.rooms}")
            custom_log(f"Current session_rooms state: {self.session_rooms}")
            
            # Get all rooms and their sizes
            room_sizes = {}
            for room_id in self.rooms:
                # Get the actual sessions in the room
                sessions = self.rooms[room_id]
                custom_log(f"Room {room_id} contains sessions: {sessions}")
                
                # Count only valid sessions
                valid_sessions = set()
                for session_id in sessions:
                    session_info = self.get_session_info(session_id)
                    if session_info:
                        valid_sessions.add(session_id)
                    else:
                        custom_log(f"Found stale session {session_id} in room {room_id}")
                
                actual_size = len(valid_sessions)
                room_sizes[room_id] = actual_size
                custom_log(f"Room {room_id} has {actual_size} valid connected users")
            
            # Reset all room sizes in Redis first
            for room_id in room_sizes:
                # Get current size before reset
                size_key = self.redis_manager._generate_secure_key("room_size", room_id)
                old_size = int(self.redis_manager.get(size_key) or "0")
                custom_log(f"Current Redis size for room {room_id}: {old_size}")
                
                # Set the new size directly
                self.redis_manager.set(size_key, str(room_sizes[room_id]))
                custom_log(f"Set room {room_id} size to {room_sizes[room_id]}")
                
            # Log final sizes for verification
            for room_id in room_sizes:
                size_key = self.redis_manager._generate_secure_key("room_size", room_id)
                current_size = int(self.redis_manager.get(size_key) or "0")
                custom_log(f"Final size for room {room_id}: {current_size}")
                
            # Clean up any stale room data
            self._cleanup_stale_rooms()
                
            custom_log("Completed room size reset")
            
        except Exception as e:
            custom_log(f"Error resetting room sizes: {str(e)}")
            
    def _cleanup_stale_rooms(self):
        """Clean up stale room data and completely remove empty rooms."""
        try:
            custom_log("Starting stale room cleanup")
            
            # Find rooms with no valid sessions
            empty_rooms = set()
            for room_id in list(self.rooms.keys()):  # Use list to avoid modification during iteration
                valid_sessions = False
                if room_id in self.rooms:  # Check again as it might have been removed
                    for session_id in self.rooms[room_id]:
                        session_info = self.get_session_info(session_id)
                        if session_info:
                            valid_sessions = True
                            break
                    
                    if not valid_sessions:
                        empty_rooms.add(room_id)
                        custom_log(f"Room {room_id} has no valid sessions")
            
            # Clean up empty rooms
            for room_id in empty_rooms:
                custom_log(f"Cleaning up empty room: {room_id}")
                
                # Remove from rooms tracking
                if room_id in self.rooms:
                    del self.rooms[room_id]
                    custom_log(f"Removed room {room_id} from rooms tracking")
                
                # Remove from all session_rooms
                for session_id in list(self.session_rooms.keys()):
                    if room_id in self.session_rooms[session_id]:
                        self.session_rooms[session_id].discard(room_id)
                        if not self.session_rooms[session_id]:
                            del self.session_rooms[session_id]
                            custom_log(f"Removed empty session {session_id} from session_rooms")
                
                # Clean up Redis data
                self._cleanup_room_data(room_id)
                
            custom_log(f"Cleaned up {len(empty_rooms)} empty rooms")
            
        except Exception as e:
            custom_log(f"Error during stale room cleanup: {str(e)}")
            
    def _cleanup_room_data(self, room_id: str):
        """Clean up all Redis data related to a room."""
        try:
            custom_log(f"Starting complete cleanup for room {room_id}")
            
            # Clean up room size
            size_key = self.redis_manager._generate_secure_key("room_size", room_id)
            self.redis_manager.delete(size_key)
            custom_log(f"Reset room size for {room_id}")
            
            # Clean up room presence data
            presence_key = self.redis_manager._generate_secure_key("room_presence", room_id)
            self.redis_manager.delete(presence_key)
            custom_log(f"Cleaned up presence data for room {room_id}")
            
            # Clean up room messages
            messages_key = self.redis_manager._generate_secure_key("room_messages", room_id)
            self.redis_manager.delete(messages_key)
            custom_log(f"Cleaned up message history for room {room_id}")
            
            # Clean up room metadata
            metadata_key = self.redis_manager._generate_secure_key("room_metadata", room_id)
            self.redis_manager.delete(metadata_key)
            custom_log(f"Cleaned up metadata for room {room_id}")
            
            # Clean up room rate limits
            for limit_type in self.rate_limits:
                rate_key = self.redis_manager._generate_secure_key("room_rate_limit", room_id, limit_type)
                self.redis_manager.delete(rate_key)
            custom_log(f"Cleaned up rate limit data for room {room_id}")
            
            # Clean up any other room-related keys using pattern matching
            self.redis_manager.cleanup_room_keys(room_id)
            
            custom_log(f"Completed cleanup for room {room_id}")
            
        except Exception as e:
            custom_log(f"Error cleaning up room data for {room_id}: {str(e)}")

    def cleanup_session(self, session_id: str):
        """Clean up all session-related data."""
        try:
            # Get session data first
            session_data = self.get_session_data(session_id)
            if not session_data:
                return
                
            # Clean up session data
            self.cleanup_session_data(session_id)
            
            # Clean up rate limit data
            if session_data.get('client_id'):
                for limit_type in self.rate_limits:
                    key = self.redis_manager._generate_secure_key("rate_limit", limit_type, session_data['client_id'])
                    self.redis_manager.delete(key)
                    
            # Clean up presence data
            if session_data.get('user_id'):
                presence_key = self.redis_manager._generate_secure_key("presence", session_data['user_id'])
                self.redis_manager.delete(presence_key)
                
            custom_log(f"Cleaned up all data for session {session_id}")
            
        except Exception as e:
            custom_log(f"Error cleaning up session: {str(e)}")

    def _cleanup_room_memberships(self, session_id: str, session_data: Optional[Dict] = None):
        """Clean up room memberships for a session."""
        try:
            custom_log(f"Cleaning up room memberships for session {session_id}")
            
            # Find all rooms this session is part of
            rooms_to_leave = []
            for room_id, members in self.rooms.items():
                if session_id in members:
                    rooms_to_leave.append(room_id)
                    
            # Leave each room
            for room_id in rooms_to_leave:
                # Remove from room
                leave_room(room_id, sid=session_id)
                
                # Update room size
                size_key = self.redis_manager._generate_secure_key("room_size", room_id)
                self.redis_manager.update_room_size(size_key, -1)
                
                # Broadcast user left event if we have user info
                if session_data and session_data.get('user_id'):
                    self.socketio.emit('user_left', {
                        'user_id': session_data['user_id'],
                        'room_id': room_id
                    }, room=room_id)
                    
                # Remove from tracking structure
                self.rooms[room_id].remove(session_id)
                
                # Clean up empty rooms
                if not self.rooms[room_id]:
                    del self.rooms[room_id]
                    self._cleanup_room_data(room_id)
                    
            custom_log(f"Completed room membership cleanup for session {session_id}")
            
        except Exception as e:
            custom_log(f"Error during room membership cleanup: {str(e)}")

    def run(self, app, **kwargs):
        """Run the WebSocket server."""
        # Initialize the socketio with the Flask app
        self.socketio.init_app(app)
        # Run the Flask app with socketio
        self.socketio.run(app, **kwargs)

    def _handle_message(self, sid: str, message: str):
        """Handle incoming WebSocket message."""
        try:
            # Get session info
            session_info = self.get_session_info(sid)
            if not session_info:
                custom_log(f"No session info found for {sid}")
                return
                
            # Validate message rate
            error = self.validator.validate_message_rate(sid)
            if error:
                custom_log(f"Rate limit exceeded for session {sid}: {error}")
                emit('error', {'message': error}, room=sid)
                return
                
            # Validate message size and content
            error = self.validator.validate_text_message_size(message)
            if error:
                custom_log(f"Message size validation failed for session {sid}: {error}")
                emit('error', {'message': error}, room=sid)
                return
                
            # Check if message should be compressed
            if self.validator.should_compress_message(message):
                message = self.validator.compress_message(message)
                
            # Process message
            try:
                data = json.loads(message)
                event = data.get('event')
                payload = data.get('payload')
                
                # Validate event
                error = self.validator.validate_event(event)
                if error:
                    custom_log(f"Event validation failed for session {sid}: {error}")
                    emit('error', {'message': error}, room=sid)
                    return
                    
                # Validate payload
                error = self.validator.validate_payload(payload)
                if error:
                    custom_log(f"Payload validation failed for session {sid}: {error}")
                    emit('error', {'message': error}, room=sid)
                    return
                    
                # Handle specific events
                if event == 'join_room':
                    room_id = payload.get('room_id')
                    if room_id:
                        self.join_room(room_id, sid)
                elif event == 'leave_room':
                    room_id = payload.get('room_id')
                    if room_id:
                        self.leave_room(room_id, sid)
                elif event == 'message':
                    room_id = payload.get('room_id')
                    message_content = payload.get('message')
                    if room_id and message_content:
                        self.broadcast_message(room_id, message_content, sid)
                        
            except json.JSONDecodeError:
                # Handle non-JSON messages
                custom_log(f"Received non-JSON message from session {sid}")
                # Process as raw message if needed
                
        except Exception as e:
            custom_log(f"Error handling message from session {sid}: {str(e)}")
            emit('error', {'message': 'Internal server error'}, room=sid)

    def broadcast_message(self, room_id: str, message: str, sender_id: str = None):
        """Broadcast a message to all users in a room."""
        try:
            # Validate message size
            error = self.validator.validate_text_message_size(message)
            if error:
                custom_log(f"Message size validation failed: {error}")
                emit('error', {'message': error}, room=sender_id)
                return
                
            # Check if message should be compressed
            if self.validator.should_compress_message(message):
                message = self.validator.compress_message(message)
                
            # Get sender info
            sender_info = self.get_session_info(sender_id) if sender_id else None
            sender_name = sender_info.get('username') if sender_info else 'Anonymous'
            
            # Prepare message data
            message_data = {
                'message': message,
                'sender': sender_name,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Broadcast to room
            emit('message', message_data, room=room_id)
            
        except Exception as e:
            custom_log(f"Error broadcasting message to room {room_id}: {str(e)}")
            if sender_id:
                emit('error', {'message': 'Failed to broadcast message'}, room=sender_id)