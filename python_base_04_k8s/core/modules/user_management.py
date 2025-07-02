from core.modules.base_module import BaseModule
from core.managers.database_manager import DatabaseManager
from core.managers.redis_manager import RedisManager
from core.managers.queue_manager import QueueManager, QueuePriority
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
            self.queue_manager = app_manager.get_queue_manager()
        else:
            # Fallback for testing or when app_manager is not provided
            self.db_manager = DatabaseManager(role="read_write")
            self.analytics_db = DatabaseManager(role="read_only")
            self.redis_manager = RedisManager()
            self.queue_manager = QueueManager()
        
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
        """Create a new user using queue system."""
        try:
            data = request.get_json()
            email = data.get('email')
            username = data.get('username')
            password = data.get('password')
            
            if not all([email, username, password]):
                return jsonify({'error': 'email, username, and password are required'}), 400
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Prepare user data for queue
            user_data = {
                'email': email,
                'username': username,
                'password': hashed_password.decode('utf-8'),  # Convert bytes to string for JSON
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
            
            # Queue the user creation task
            task_data = {
                'operation': 'insert',
                'collection': 'users',
                'data': user_data
            }
            
            task_id = self.queue_manager.enqueue(
                queue_name='default',
                task_type='user_creation',
                task_data=task_data,
                priority=QueuePriority.NORMAL
            )
            
            return jsonify({
                'message': 'User creation is being processed',
                'task_id': task_id,
                'email': email,
                'username': username,
                'status': 'pending'
            }), 202  # 202 Accepted - request is being processed
            
        except Exception as e:
            self.logger.error(f"Error queuing user creation: {e}")
            return jsonify({'error': 'Failed to queue user creation'}), 500

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
        """Update user information using queue system."""
        try:
            data = request.get_json()
            update_data = {'updated_at': datetime.utcnow().isoformat()}
            
            # Only update allowed fields
            allowed_fields = ['username', 'email', 'status']
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]
            
            # Queue the user update task
            task_data = {
                'operation': 'update',
                'collection': 'users',
                'query': {'_id': user_id},
                'update_data': update_data
            }
            
            task_id = self.queue_manager.enqueue(
                queue_name='default',
                task_type='user_update',
                task_data=task_data,
                priority=QueuePriority.NORMAL
            )
            
            return jsonify({
                'message': 'User update is being processed',
                'task_id': task_id,
                'user_id': user_id,
                'status': 'pending'
            }), 202  # 202 Accepted - request is being processed
                
        except Exception as e:
            self.logger.error(f"Error queuing user update: {e}")
            return jsonify({'error': 'Failed to queue user update'}), 500

    def delete_user(self, user_id):
        """Delete a user using queue system."""
        try:
            # Queue the user deletion task
            task_data = {
                'operation': 'delete',
                'collection': 'users',
                'query': {'_id': user_id}
            }
            
            task_id = self.queue_manager.enqueue(
                queue_name='high_priority',
                task_type='user_deletion',
                task_data=task_data,
                priority=QueuePriority.HIGH
            )
            
            return jsonify({
                'message': 'User deletion is being processed',
                'task_id': task_id,
                'user_id': user_id,
                'status': 'pending'
            }), 202  # 202 Accepted - request is being processed
                
        except Exception as e:
            self.logger.error(f"Error queuing user deletion: {e}")
            return jsonify({'error': 'Failed to queue user deletion'}), 500

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