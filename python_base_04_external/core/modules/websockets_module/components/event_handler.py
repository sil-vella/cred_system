from typing import Dict, Any, Optional
from datetime import datetime
from tools.logger.custom_logging import custom_log
from flask import request
from ..websocket_manager import WebSocketManager
from core.managers.redis_manager import RedisManager
from .room_manager import RoomManager, RoomPermission
from .session_manager import SessionManager
from .result_handler import ResultHandler
from .broadcast_manager import BroadcastManager
import time
from utils.config.config import Config

class EventHandler:
    def __init__(self, websocket_manager: WebSocketManager, room_manager: RoomManager, 
                 session_manager: SessionManager, redis_manager: RedisManager,
                 result_handler: ResultHandler, broadcast_manager: BroadcastManager):
        self.websocket_manager = websocket_manager
        self.room_manager = room_manager
        self.session_manager = session_manager
        self.redis_manager = redis_manager
        self.result_handler = result_handler
        self.broadcast_manager = broadcast_manager

    def handle_connect(self, data=None):
        """Handle new WebSocket connections with security checks."""
        custom_log(f"DEBUG - EventHandler.handle_connect called with data: {data}")
        session_id = request.sid
        origin = request.headers.get('Origin', '')
        client_id = request.headers.get('X-Client-ID', session_id)
        token = request.args.get('token')  # Get token from query parameters
        
        # For testing, allow all origins
        if origin == 'null' or not origin:
            origin = 'http://localhost:5000'
            
        # Validate origin
        if not self.websocket_manager.validate_origin(origin):
            custom_log(f"Invalid origin rejected: {origin}")
            return self.result_handler.create_result('connect', error='Invalid origin')
            
        # Check rate limits
        if not self.websocket_manager.check_rate_limit(client_id, 'connections'):
            custom_log(f"Rate limit exceeded for client: {client_id}")
            return self.result_handler.create_result('connect', error='Rate limit exceeded')
            
        # Validate JWT token
        if not token:
            custom_log("No token provided for WebSocket connection")
            return self.result_handler.create_result('connect', error='Authentication required')
            
        # Validate token using JWT manager directly
        from core.managers.jwt_manager import TokenType
        payload = self.websocket_manager._jwt_manager.verify_token(token, TokenType.ACCESS) or \
                 self.websocket_manager._jwt_manager.verify_token(token, TokenType.WEBSOCKET)
        if not payload:
            custom_log("Invalid token for WebSocket connection")
            return self.result_handler.create_result('connect', error='Invalid authentication')
            
        custom_log(f"DEBUG - JWT payload: {payload}")
            
        # Update rate limits
        self.websocket_manager.update_rate_limit(client_id, 'connections')
        
        # Create session data for WebSocket manager
        session_data = {
            'user_id': str(payload.get('user_id')),
            'username': payload.get('username'),
            'token': token,
            'token_type': payload.get('type'),
            'connected_at': datetime.utcnow().isoformat(),
            'last_active': datetime.utcnow().isoformat(),
            'rooms': [],
            'client_id': client_id,
            'origin': origin
        }
        
        # Store session data using WebSocket manager
        custom_log(f"DEBUG - Storing session data: {session_data}")
        self.websocket_manager.store_session_data(session_id, session_data)
        
        # Send session data to client
        self.broadcast_manager.send_to_session(session_id, 'session_data', session_data)
        
        custom_log(f"New WebSocket connection: {session_id} from {origin} for user {session_data['user_id']}")
        return self.result_handler.create_result('connect', data={'session_id': session_id})

    def handle_disconnect(self, data=None):
        """Handle WebSocket disconnections with cleanup."""
        session_id = request.sid
        
        # Get user data before cleanup
        session_data = self.websocket_manager.get_session_data(session_id)
        if session_data:
            username = session_data.get('username')
            if username:
                # Leave all rooms before cleanup
                for room_id in session_data.get('rooms', []):
                    self.websocket_manager.leave_room(room_id, session_id)
                    
                    # Broadcast user left event
                    self.broadcast_manager.broadcast_to_room(
                        room_id,
                        'user_left',
                        {'username': username}
                    )
        
        # Clean up session data using WebSocket manager
        self.websocket_manager.cleanup_session_data(session_id)
        custom_log(f"WebSocket disconnected: {session_id}")

    async def handle_join(self, session_id: str, data: dict = None) -> dict:
        """Handle room join event."""
        try:
            # Ensure data is a dictionary
            if data is None:
                data = {}
                
            # Validate data is a dictionary
            if not isinstance(data, dict):
                custom_log(f"Invalid data format for join event: {data}")
                await self.broadcast_manager.send_to_session(
                    session_id,
                    'join_room_error',
                    {'error': 'Invalid data format'}
                )
                return {'status': 'error', 'message': 'Invalid data format'}

            # Extract room_id from data
            room_id = data.get('room_id')
            if not room_id:
                custom_log(f"Missing room_id in join event data: {data}")
                await self.broadcast_manager.send_to_session(
                    session_id,
                    'join_room_error',
                    {'error': 'Missing room_id'}
                )
                return {'status': 'error', 'message': 'Missing room_id'}

            # Get session data from WebSocket manager
            session_data = self.websocket_manager.get_session_data(session_id)
            if not session_data:
                custom_log(f"Session {session_id} not found")
                await self.broadcast_manager.send_to_session(
                    session_id,
                    'join_room_error',
                    {'error': 'Session not found'}
                )
                return {'status': 'error', 'message': 'Session not found'}

            # Check if user is already in the room
            if room_id in session_data.get('rooms', set()):
                custom_log(f"User {session_data['user_id']} is already in room {room_id}")
                await self.broadcast_manager.send_to_session(
                    session_id,
                    'join_room_error',
                    {'error': 'Already in room'}
                )
                return {'status': 'error', 'message': 'Already in room'}

            # Try to join the room using websocket_manager
            if self.websocket_manager.join_room(room_id, session_id):
                # Get current room members
                room_members = self.broadcast_manager.get_room_members(room_id)
                room_data = self.room_manager.get_room_permissions(room_id)

                # Send join confirmation to the user
                await self.broadcast_manager.send_to_session(
                    session_id,
                    'join_room_success',
                    {
                        'room_id': room_id,
                        'current_size': len(room_members),
                        'max_size': room_data.get('max_size', 2)
                    }
                )

                # Send current room state to the user
                await self.broadcast_manager.send_to_session(
                    session_id,
                    'room_state',
                    {
                        'room_id': room_id,
                        'members': list(room_members),
                        'owner_id': room_data.get('owner_id'),
                        'permission': room_data.get('permission'),
                        'allowed_users': list(room_data.get('allowed_users', set())),
                        'allowed_roles': list(room_data.get('allowed_roles', set()))
                    }
                )

                custom_log(f"Session {session_id} successfully joined room {room_id}")
                return {'status': 'success', 'room_id': room_id}
            else:
                custom_log(f"Failed to join room {room_id} for session {session_id}")
                await self.broadcast_manager.send_to_session(
                    session_id,
                    'join_room_error',
                    {'error': 'Failed to join room'}
                )
                return {'status': 'error', 'message': 'Failed to join room'}

        except Exception as e:
            custom_log(f"Error handling join event: {str(e)}")
            await self.broadcast_manager.send_to_session(
                session_id,
                'join_room_error',
                {'error': str(e)}
            )
            return {'status': 'error', 'message': str(e)}

    def handle_leave(self, data):
        """Handle leave room event."""
        try:
            room_id = data.get('room_id')
            if not room_id:
                custom_log("No room_id provided in leave event")
                return self.result_handler.create_result('leave', error='No room_id provided')
                
            # Get session data from WebSocket manager
            session_id = request.sid
            session_data = self.websocket_manager.get_session_data(session_id)
            if not session_data:
                custom_log("No session data found for leave event")
                return self.result_handler.create_result('leave', error='No session data found')
                
            # Check if user is in the room
            if room_id not in session_data.get('rooms', set()):
                custom_log(f"User {session_data.get('username')} not in room {room_id}")
                return self.result_handler.create_result('leave', error='Not in room')
                
            # Leave room
            self.websocket_manager.leave_room(room_id, session_id)
            
            # Broadcast leave event
            self.broadcast_manager.broadcast_to_room(room_id, 'user_left', {
                'room_id': room_id,
                'user_id': session_data.get('user_id'),
                'username': session_data.get('username')
            })
            
            custom_log(f"User {session_data.get('username')} left room {room_id}")
            return self.result_handler.create_result('leave', data={'room_id': room_id})
            
        except Exception as e:
            custom_log(f"Error in leave handler: {str(e)}")
            return self.result_handler.create_result('leave', error=str(e))

    def handle_message(self, data):
        """Handle message event."""
        try:
            room_id = data.get('room_id')
            message = data.get('message')
            if not room_id or not message:
                custom_log("Missing room_id or message in message event")
                return self.result_handler.create_result('message', error='Missing room_id or message')
                
            # Get session data from WebSocket manager
            session_id = request.sid
            session_data = self.websocket_manager.get_session_data(session_id)
            if not session_data:
                custom_log("No session data found for message event")
                return self.result_handler.create_result('message', error='No session data found')
                
            # Broadcast message
            self.broadcast_manager.broadcast_to_room(room_id, 'message', {
                'room_id': room_id,
                'user_id': session_data.get('user_id'),
                'username': session_data.get('username'),
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            })
            
            custom_log(f"Message from {session_data.get('username')} in room {room_id}")
            return self.result_handler.create_result('message', data={'room_id': room_id})
            
        except Exception as e:
            custom_log(f"Error in message handler: {str(e)}")
            return self.result_handler.create_result('message', error=str(e))

    def handle_get_users(self, data):
        """Handle get users event."""
        try:
            room_id = data.get('room_id')
            if not room_id:
                custom_log("No room_id provided in get users event")
                return self.result_handler.create_result('get_users', error='No room_id provided')
                
            # Get session data from WebSocket manager
            session_id = request.sid
            session_data = self.websocket_manager.get_session_data(session_id)
            if not session_data:
                custom_log("No session data found for get users event")
                return self.result_handler.create_result('get_users', error='No session data found')
                
            # Get room members
            room_members = self.broadcast_manager.get_room_members(room_id)
            
            # Get user data for each member
            users = []
            for member_id in room_members:
                member_session = self.websocket_manager.get_session_data(member_id)
                if member_session:
                    users.append({
                        'user_id': member_session.get('user_id'),
                        'username': member_session.get('username')
                    })
            
            # Send user list to client
            self.broadcast_manager.send_to_session(session_id, 'user_list', {
                'room_id': room_id,
                'users': users
            })
            
            custom_log(f"User list sent to {session_data.get('username')} for room {room_id}")
            return self.result_handler.create_result('get_users', data={'users': users})
            
        except Exception as e:
            custom_log(f"Error in get users handler: {str(e)}")
            return self.result_handler.create_result('get_users', error=str(e))

    def handle_create_room(self, data, session_data=None):
        """Handle create room event."""
        try:
            # Get session data from WebSocket manager if not provided
            session_id = request.sid
            if not session_data:
                session_data = self.websocket_manager.get_session_data(session_id)
                if not session_data:
                    custom_log("No session data found for create room event")
                    return self.result_handler.create_result('create_room', error='No session data found')
            
            # Handle both dictionary and string inputs for data
            if isinstance(data, str):
                data = {'user_id': data}
            
            # Get user ID from session data
            user_id = session_data.get('user_id')
            if not user_id:
                custom_log("No user_id found in session data")
                return self.result_handler.create_result('create_room', error='No user_id found in session')
                
            # Generate room ID in format: {user_id}-ddyyhhmm
            now = datetime.now()
            room_id = f"{user_id}-{now.strftime('%d%y%H%M')}"
            
            # Get room parameters from data
            permission = data.get('permission', 'public')
            allowed_users = set(data.get('allowed_users', [])) if data.get('allowed_users') else set()
            allowed_roles = set(data.get('allowed_roles', [])) if data.get('allowed_roles') else set()
            
            # Validate permission type
            if permission not in ['public', 'private', 'restricted', 'owner_only']:
                permission = 'public'
            
            # For public rooms, no need to specify allowed_users/roles
            if permission == 'public':
                allowed_users = set()
                allowed_roles = set()
            
            custom_log(f"Creating room with ID: {room_id}, permission: {permission}")
                
            # Create room with specified permission
            room_data = self.room_manager.create_room(
                room_id,
                RoomPermission(permission),
                user_id,
                allowed_users,
                allowed_roles
            )
            
            if not room_data:
                custom_log(f"Failed to create room {room_id}")
                return self.result_handler.create_result('create_room', error='Failed to create room')
                
            # Join the room
            if not self.websocket_manager.join_room(room_id, session_id):
                custom_log(f"Failed to join room {room_id}")
                return self.result_handler.create_result('create_room', error='Failed to join room')
                
            # Add room to session
            try:
                self.session_manager.add_room_to_session(session_id, room_id)
            except Exception as e:
                custom_log(f"Error adding room to session: {str(e)}")
                # Continue anyway as the room is created
            
            # Generate join link
            join_link = f"{Config.APP_URL}/join/{room_id}"
            
            # Add join link to room data
            room_data['join_link'] = join_link
            
            # Broadcast room created event
            self.broadcast_manager.broadcast_to_room(room_id, 'room_created', {
                'room_id': room_id,
                'owner_id': user_id,
                'owner_username': session_data.get('username'),
                'permission': permission,
                'allowed_users': list(allowed_users),
                'allowed_roles': list(allowed_roles),
                'join_link': join_link
            })
            
            custom_log(f"Room {room_id} created by {session_data.get('username')} with {permission} permission")
            return self.result_handler.create_result('create_room', data=room_data)
            
        except Exception as e:
            custom_log(f"Error in create room handler: {str(e)}")
            return self.result_handler.create_result('create_room', error=str(e))

    def _send_room_state(self, room_id: str, session_id: str):
        """Send current room state to a session."""
        try:
            # Get room members
            room_members = self.broadcast_manager.get_room_members(room_id)
            
            # Get user data for each member
            users = []
            for member_id in room_members:
                member_session = self.session_manager.get_session(member_id)
                if member_session:
                    users.append({
                        'user_id': member_session.get('user_id'),
                        'username': member_session.get('username')
                    })
            
            # Get counter value
            counter_key = f"button_counter:{room_id}"
            current_count = self.redis_manager.get(counter_key) or 0
            
            # Send room state to client
            self.broadcast_manager.send_to_session(session_id, 'room_state', {
                'room_id': room_id,
                'users': users,
                'counter': current_count
            })
            
            custom_log(f"Room state sent to session {session_id} for room {room_id}")
            
        except Exception as e:
            custom_log(f"Error sending room state: {str(e)}") 