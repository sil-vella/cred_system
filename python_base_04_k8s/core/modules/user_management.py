from core.modules.base_module import BaseModule
from core.managers.database_manager import DatabaseManager
from core.managers.redis_manager import RedisManager
from tools.logger.custom_logging import custom_log
from flask import request, jsonify
from datetime import datetime
from typing import Dict, Any
import bcrypt


class UserManagementModule(BaseModule):
    def __init__(self, app_manager=None):
        """Initialize the UserManagementModule."""
        super().__init__(app_manager)
        
        # Set dependencies
        self.dependencies = ["connection_api"]
        
        # Initialize managers
        self.db_manager = DatabaseManager(role="read_write")
        self.analytics_db = DatabaseManager(role="read_only")
        self.redis_manager = RedisManager()
        
        custom_log("UserManagementModule created")

    def initialize(self, app):
        """Initialize the UserManagementModule with Flask app."""
        self.app = app
        self.initialize_database()
        self.register_routes()
        self._initialized = True
        custom_log("UserManagementModule initialized")

    def register_routes(self):
        """Register user management routes."""
        self._register_route_helper("/users", self.create_user, methods=["POST"])
        self._register_route_helper("/users/<user_id>", self.get_user, methods=["GET"])
        self._register_route_helper("/users/<user_id>", self.update_user, methods=["PUT"])
        self._register_route_helper("/users/<user_id>", self.delete_user, methods=["DELETE"])
        self._register_route_helper("/users/search", self.search_users, methods=["POST"])
        custom_log(f"UserManagementModule registered {len(self.registered_routes)} routes")

    def initialize_database(self):
        """Initialize user-related database collections."""
        try:
            self.analytics_db.db.users.create_index("email", unique=True)
            self.analytics_db.db.users.create_index("username")
            custom_log("✅ User collections initialized")
        except Exception as e:
            custom_log(f"❌ Error initializing user collections: {e}")
            raise

    def create_user(self):
        """Create a new user."""
        try:
            data = request.get_json()
            email = data.get('email')
            username = data.get('username')
            password = data.get('password')
            
            if not all([email, username, password]):
                return jsonify({'error': 'email, username, and password are required'}), 400
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            user_data = {
                'email': email,
                'username': username,
                'password': hashed_password,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'status': 'active'
            }
            
            user_id = self.db_manager.insert("users", user_data)
            
            return jsonify({
                'user_id': user_id,
                'email': email,
                'username': username,
                'status': 'active'
            }), 201
            
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return jsonify({'error': 'Failed to create user'}), 500

    def get_user(self, user_id):
        """Get user by ID."""
        try:
            user = self.analytics_db.find_one("users", {"_id": user_id})
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Remove password from response
            user.pop('password', None)
            return jsonify(user), 200
            
        except Exception as e:
            self.logger.error(f"Error getting user: {e}")
            return jsonify({'error': 'Failed to get user'}), 500

    def update_user(self, user_id):
        """Update user information."""
        try:
            data = request.get_json()
            update_data = {'updated_at': datetime.utcnow()}
            
            # Only update allowed fields
            allowed_fields = ['username', 'email', 'status']
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]
            
            result = self.db_manager.update("users", {"_id": user_id}, update_data)
            
            if result > 0:
                return jsonify({'message': 'User updated successfully'}), 200
            else:
                return jsonify({'error': 'User not found'}), 404
                
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            return jsonify({'error': 'Failed to update user'}), 500

    def delete_user(self, user_id):
        """Delete a user."""
        try:
            result = self.db_manager.delete("users", {"_id": user_id})
            
            if result > 0:
                return jsonify({'message': 'User deleted successfully'}), 200
            else:
                return jsonify({'error': 'User not found'}), 404
                
        except Exception as e:
            self.logger.error(f"Error deleting user: {e}")
            return jsonify({'error': 'Failed to delete user'}), 500

    def search_users(self):
        """Search users with filters."""
        try:
            data = request.get_json()
            query = {}
            
            if 'username' in data:
                query['username'] = {'$regex': data['username'], '$options': 'i'}
            if 'email' in data:
                query['email'] = {'$regex': data['email'], '$options': 'i'}
            if 'status' in data:
                query['status'] = data['status']
            
            users = self.analytics_db.find("users", query)
            
            # Remove passwords from response
            for user in users:
                user.pop('password', None)
            
            return jsonify({'users': users}), 200
            
        except Exception as e:
            self.logger.error(f"Error searching users: {e}")
            return jsonify({'error': 'Failed to search users'}), 500

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for UserManagementModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        return health_status 