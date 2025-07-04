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
        
        # Use centralized managers from app_manager instead of creating new instances
        if app_manager:
            self.db_manager = app_manager.get_db_manager(role="read_write")
            self.analytics_db = app_manager.get_db_manager(role="read_only")
            self.redis_manager = app_manager.get_redis_manager()
        else:
            # Fallback for testing or when app_manager is not provided
            self.db_manager = DatabaseManager(role="read_write")
            self.analytics_db = DatabaseManager(role="read_only")
            self.redis_manager = RedisManager()
        
        custom_log("UserManagementModule created with shared managers")

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
        """Verify database connection for user operations."""
        try:
            # Check if database is available
            if not self.analytics_db.available:
                custom_log("⚠️ Database unavailable for user operations - running with limited functionality")
                return
                
            # Simple connection test
            self.analytics_db.db.command('ping')
            custom_log("✅ User database connection verified")
        except Exception as e:
            custom_log(f"⚠️ User database connection verification failed: {e}")
            custom_log("⚠️ User operations will be limited - suitable for local development")

    def create_user(self):
        """Create a new user with queued database operation."""
        try:
            data = request.get_json()
            email = data.get('email')
            username = data.get('username')
            password = data.get('password')
            
            if not all([email, username, password]):
                return jsonify({'error': 'email, username, and password are required'}), 400
            
            # Check if user already exists
            existing_user = self.analytics_db.find_one("users", {"email": email})
            if existing_user:
                return jsonify({'error': 'User with this email already exists'}), 409
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Prepare user data
            user_data = {
                'email': email,
                'username': username,
                'password': hashed_password.decode('utf-8'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
            
            # Insert user using queue system
            user_id = self.db_manager.insert("users", user_data)
            
            if user_id:
                # Remove password from response
                user_data.pop('password', None)
                user_data['_id'] = user_id
                
                return jsonify({
                    'message': 'User created successfully',
                    'user': user_data,
                    'status': 'created'
                }), 201
            else:
                return jsonify({'error': 'Failed to create user'}), 500
            
        except Exception as e:
            custom_log(f"Error creating user: {e}")
            return jsonify({'error': 'Failed to create user'}), 500

    def get_user(self, user_id):
        """Get user by ID with queued operation."""
        try:
            user = self.analytics_db.find_one("users", {"_id": user_id})
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Remove password from response
            user.pop('password', None)
            return jsonify(user), 200
            
        except Exception as e:
            custom_log(f"Error getting user: {e}")
            return jsonify({'error': 'Failed to get user'}), 500

    def update_user(self, user_id):
        """Update user information with queued operation."""
        try:
            data = request.get_json()
            update_data = {'updated_at': datetime.utcnow().isoformat()}
            
            # Only update allowed fields
            allowed_fields = ['username', 'email', 'status']
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]
            
            # Update user using queue system
            modified_count = self.db_manager.update("users", {"_id": user_id}, {"$set": update_data})
            
            if modified_count > 0:
                return jsonify({
                    'message': 'User updated successfully',
                    'user_id': user_id,
                    'status': 'updated'
                }), 200
            else:
                return jsonify({'error': 'User not found or no changes made'}), 404
                
        except Exception as e:
            custom_log(f"Error updating user: {e}")
            return jsonify({'error': 'Failed to update user'}), 500

    def delete_user(self, user_id):
        """Delete a user with queued operation."""
        try:
            # Delete user using queue system
            deleted_count = self.db_manager.delete("users", {"_id": user_id})
            
            if deleted_count > 0:
                return jsonify({
                    'message': 'User deleted successfully',
                    'user_id': user_id,
                    'status': 'deleted'
                }), 200
            else:
                return jsonify({'error': 'User not found'}), 404
                
        except Exception as e:
            custom_log(f"Error deleting user: {e}")
            return jsonify({'error': 'Failed to delete user'}), 500

    def search_users(self):
        """Search users with filters using queued operation."""
        try:
            data = request.get_json()
            query = {}
            
            if 'username' in data:
                query['username'] = {'$regex': data['username'], '$options': 'i'}
            if 'email' in data:
                query['email'] = {'$regex': data['email'], '$options': 'i'}
            if 'status' in data:
                query['status'] = data['status']
            
            # Search users using queue system
            users = self.analytics_db.find("users", query)
            
            # Remove passwords from response
            for user in users:
                user.pop('password', None)
            
            return jsonify({'users': users}), 200
            
        except Exception as e:
            custom_log(f"Error searching users: {e}")
            return jsonify({'error': 'Failed to search users'}), 500

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for UserManagementModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        
        # Add database queue status
        try:
            queue_status = self.db_manager.get_queue_status()
            health_status['details'] = {
                'database_queue': {
                    'queue_size': queue_status['queue_size'],
                    'worker_alive': queue_status['worker_alive'],
                    'queue_enabled': queue_status['queue_enabled'],
                    'pending_results': queue_status['pending_results']
                }
            }
        except Exception as e:
            health_status['details'] = {'database_queue': f'error: {str(e)}'}
        
        return health_status 