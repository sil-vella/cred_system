from typing import Dict, Any, Optional, Set
from datetime import datetime
from enum import Enum
from tools.logger.custom_logging import custom_log

class RoomPermission(Enum):
    PUBLIC = "public"  # Anyone can join
    PRIVATE = "private"  # Only invited users can join
    RESTRICTED = "restricted"  # Only users with specific roles can join
    OWNER_ONLY = "owner_only"  # Only room owner can join

class RoomManager:
    def __init__(self):
        self.room_permissions = {}
        self._initialize_room_permissions()

    def _initialize_room_permissions(self):
        """Initialize default room permissions."""
        # Default room permissions
        self.room_permissions = {
            "button_counter_room": {
                'permission': RoomPermission.PUBLIC,
                'owner_id': None,
                'allowed_users': set(),
                'allowed_roles': set(),
                'created_at': datetime.utcnow().isoformat()
            }
        }
        custom_log("Room permissions initialized")

    def check_room_access(self, room_id: str, user_id: str, user_roles: Set[str]) -> bool:
        """Check if a user has permission to join a room."""
        # First check in-memory permissions
        if room_id in self.room_permissions:
            room_data = self.room_permissions[room_id]
            permission = room_data['permission']
            
            # Check permission type
            if permission == RoomPermission.PUBLIC.value:
                return True
                
            if permission == RoomPermission.PRIVATE.value:
                return user_id in room_data['allowed_users']
                
            if permission == RoomPermission.RESTRICTED.value:
                return bool(room_data['allowed_roles'] & user_roles)
                
            if permission == RoomPermission.OWNER_ONLY.value:
                return user_id == room_data['owner_id']
        
        # If not in memory, check Redis
        from core.managers.redis_manager import RedisManager
        redis_manager = RedisManager()
        permissions_key = redis_manager._generate_secure_key("room_permissions", room_id)
        room_data = redis_manager.get(permissions_key)
        
        if not room_data:
            custom_log(f"Room {room_id} not found")
            return False
            
        permission = room_data.get('permission')
        
        # Check permission type
        if permission == RoomPermission.PUBLIC.value:
            return True
            
        if permission == RoomPermission.PRIVATE.value:
            allowed_users = set(room_data.get('allowed_users', []))
            return user_id in allowed_users
            
        if permission == RoomPermission.RESTRICTED.value:
            allowed_roles = set(room_data.get('allowed_roles', []))
            return bool(allowed_roles & user_roles)
            
        if permission == RoomPermission.OWNER_ONLY.value:
            return user_id == room_data.get('owner_id')
            
        return False

    def create_room(self, room_id: str, permission: RoomPermission, owner_id: str, 
                   allowed_users: Set[str] = None, allowed_roles: Set[str] = None) -> Dict[str, Any]:
        """Create a new room with specified permissions."""
        if room_id in self.room_permissions:
            raise ValueError(f"Room {room_id} already exists")
            
        # Ensure allowed_users and allowed_roles are empty sets if None
        if allowed_users is None:
            allowed_users = set()
        if allowed_roles is None:
            allowed_roles = set()
            
        room_data = {
            'permission': permission.value,  # Store the string value instead of enum
            'owner_id': owner_id,
            'allowed_users': list(allowed_users),
            'allowed_roles': list(allowed_roles),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Store in memory
        self.room_permissions[room_id] = room_data
        
        # Also store in Redis for WebSocketManager to find
        from core.managers.redis_manager import RedisManager
        redis_manager = RedisManager()
        
        # Store room permissions
        permissions_key = redis_manager._generate_secure_key("room_permissions", room_id)
        redis_manager.set(permissions_key, room_data)
        
        # Initialize room size
        size_key = redis_manager._generate_secure_key("room_size", room_id)
        redis_manager.set(size_key, "0")
        
        custom_log(f"Created new room {room_id} with permission {permission.value}")
        return room_data

    def update_room_permissions(self, room_id: str, permission: RoomPermission = None,
                              allowed_users: Set[str] = None, allowed_roles: Set[str] = None) -> Dict[str, Any]:
        """Update room permissions."""
        # Check if room exists in memory
        if room_id in self.room_permissions:
            room_data = self.room_permissions[room_id]
            
            if permission:
                room_data['permission'] = permission.value
            if allowed_users is not None:
                room_data['allowed_users'] = list(allowed_users)
            if allowed_roles is not None:
                room_data['allowed_roles'] = list(allowed_roles)
        else:
            # Check Redis
            from core.managers.redis_manager import RedisManager
            redis_manager = RedisManager()
            permissions_key = redis_manager._generate_secure_key("room_permissions", room_id)
            room_data = redis_manager.get(permissions_key)
            
            if not room_data:
                raise ValueError(f"Room {room_id} not found")
        
            if permission:
                room_data['permission'] = permission.value
            if allowed_users is not None:
                room_data['allowed_users'] = list(allowed_users)
            if allowed_roles is not None:
                room_data['allowed_roles'] = list(allowed_roles)
            
            # Update in Redis
            redis_manager.set(permissions_key, room_data)
            
        custom_log(f"Updated permissions for room {room_id}")
        return room_data

    def get_room_permissions(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get room permissions."""
        # First check in memory
        if room_id in self.room_permissions:
            return self.room_permissions[room_id]
        
        # Check Redis
        from core.managers.redis_manager import RedisManager
        redis_manager = RedisManager()
        permissions_key = redis_manager._generate_secure_key("room_permissions", room_id)
        return redis_manager.get(permissions_key)

    def delete_room(self, room_id: str):
        """Delete a room and its permissions."""
        # Remove from memory
        if room_id in self.room_permissions:
            del self.room_permissions[room_id]
        
        # Remove from Redis
        from core.managers.redis_manager import RedisManager
        redis_manager = RedisManager()
        
        # Delete room permissions
        permissions_key = redis_manager._generate_secure_key("room_permissions", room_id)
        redis_manager.delete(permissions_key)
        
        # Delete room size
        size_key = redis_manager._generate_secure_key("room_size", room_id)
        redis_manager.delete(size_key)
        
        custom_log(f"Deleted room {room_id}") 

    def list_rooms(self, owner_id: str = None) -> list:
        """List all rooms, optionally filtered by owner."""
        rooms = []
        
        # Get rooms from memory
        for room_id, room_data in self.room_permissions.items():
            if owner_id is None or room_data.get('owner_id') == owner_id:
                rooms.append({
                    'room_id': room_id,
                    'owner_id': room_data.get('owner_id'),
                    'permission': room_data.get('permission'),
                    'created_at': room_data.get('created_at'),
                    'allowed_users': list(room_data.get('allowed_users', [])),
                    'allowed_roles': list(room_data.get('allowed_roles', []))
                })
        
        # Get rooms from Redis
        from core.managers.redis_manager import RedisManager
        redis_manager = RedisManager()
        room_keys = redis_manager.get_keys("room_permissions:*")
        
        for key in room_keys:
            room_id = key.split(":", 1)[1]
            room_data = redis_manager.get(key)
            
            if room_data and (owner_id is None or room_data.get('owner_id') == owner_id):
                # Check if not already in memory
                if room_id not in self.room_permissions:
                    rooms.append({
                        'room_id': room_id,
                        'owner_id': room_data.get('owner_id'),
                        'permission': room_data.get('permission'),
                        'created_at': room_data.get('created_at'),
                        'allowed_users': list(room_data.get('allowed_users', [])),
                        'allowed_roles': list(room_data.get('allowed_roles', []))
                    })
        
        return rooms

    def get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a room."""
        # First check in memory
        if room_id in self.room_permissions:
            room_data = self.room_permissions[room_id].copy()
            room_data['room_id'] = room_id
            return room_data
        
        # Check Redis
        from core.managers.redis_manager import RedisManager
        redis_manager = RedisManager()
        permissions_key = redis_manager._generate_secure_key("room_permissions", room_id)
        room_data = redis_manager.get(permissions_key)
        
        if room_data:
            room_data['room_id'] = room_id
            return room_data
        
        return None 