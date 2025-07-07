import os
import json
from tools.logger.custom_logging import custom_log, log_function_call
from utils.config.config import Config
from core.managers.redis_manager import RedisManager
from core.managers.jwt_manager import JWTManager, TokenType
from core.managers.database_manager import DatabaseManager
from tools.error_handling import ErrorHandler
from datetime import datetime, timedelta
import time
import uuid
import logging
from flask import request, jsonify
from typing import Dict, Any
from core.modules.base_module import BaseModule


class ConnectionAPI(BaseModule):
    def __init__(self, app_manager=None):
        """Initialize the ConnectionAPI module with Redis and database connections."""
        super().__init__(app_manager)
        
        # Set dependencies (this module has no dependencies)
        self.dependencies = []
        
        # Use centralized managers from app_manager instead of creating new instances
        if app_manager:
            self.db_manager = app_manager.get_db_manager(role="read_write")
            self.analytics_db = app_manager.get_db_manager(role="read_only")
            self.admin_db = app_manager.get_db_manager(role="admin")
            self.redis_manager = app_manager.get_redis_manager()
        else:
            # Fallback for testing or when app_manager is not provided
            self.db_manager = DatabaseManager(role="read_write")
            self.analytics_db = DatabaseManager(role="read_only")
            self.admin_db = DatabaseManager(role="admin")
            self.redis_manager = RedisManager()
        
        # Use centralized JWT manager from app_manager if available
        if app_manager:
            self.jwt_manager = JWTManager(redis_manager=self.redis_manager)
        else:
            self.jwt_manager = JWTManager()  # Fallback for testing
        
        # Initialize API Key Manager
        from core.managers.api_key_manager import APIKeyManager
        self.api_key_manager = APIKeyManager(self.redis_manager)
        
        self.error_handler = ErrorHandler()  # Initialize error handler
        
        # Session management settings
        self.session_timeout = 3600  # 1 hour in seconds
        self.max_concurrent_sessions = 1  # Only one session allowed per user
        self.session_check_interval = 300  # 5 minutes in seconds

        custom_log(f"ConnectionAPI module created with shared managers")

    def initialize(self, app_manager):
        """Initialize the ConnectionAPI with AppManager."""
        self.app_manager = app_manager
        self.app = app_manager.flask_app
        custom_log(f"ConnectionAPI initialized with AppManager")
        
        # Ensure collections exist in the database
        self.initialize_database()
        
        # Register routes
        self.register_routes()
        
        # Mark as initialized
        self._initialized = True

    def register_routes(self):
        """Register all ConnectionAPI routes."""
        custom_log("Registering ConnectionAPI routes...")
        
        # Register core routes
        self._register_route_helper("/", self.home, methods=["GET"])
        self._register_route_helper("/auth/refresh", self.refresh_token_endpoint, methods=["POST"])
        self._register_route_helper("/get-db-data", self.get_all_database_data, methods=["GET"])
        
        # Register API key management routes
        self._register_route_helper("/api-keys/generate", self.generate_api_key, methods=["POST"])
        self._register_route_helper("/api-keys/validate", self.validate_api_key, methods=["POST"])
        self._register_route_helper("/api-keys/revoke", self.revoke_api_key, methods=["POST"])
        self._register_route_helper("/api-keys/list", self.list_api_keys, methods=["GET"])
        self._register_route_helper("/api-keys/stored", self.list_stored_api_keys, methods=["GET"])
        
        custom_log(f"ConnectionAPI registered {len(self.registered_routes)} routes")

    def initialize_database(self):
        """Verify database connection without creating collections or indexes."""
        custom_log("⚙️ Verifying database connection...")
        if self._verify_database_connection():
            custom_log("✅ Database connection verified.")
        else:
            custom_log("⚠️ Database connection unavailable - running with limited functionality")

    def _verify_database_connection(self) -> bool:
        """Verify database connection without creating anything."""
        try:
            # Check if database is available
            if not self.admin_db.available:
                custom_log("⚠️ Database unavailable - connection verification skipped")
                return False
                
            # Simple connection test - just ping the database
            self.admin_db.db.command('ping')
            custom_log("✅ Database connection verified successfully")
            return True
        except Exception as e:
            custom_log(f"⚠️ Database connection verification failed: {e}")
            custom_log("⚠️ Database operations will be limited - suitable for local development")
            return False

    def home(self):
        """Handle the root route."""
        return {"message": "ConnectionAPI module is running", "version": "2.0", "module": "connection_api"}

    def get_all_database_data(self):
        """Get all data from all collections in the database."""
        try:
            # Use the database manager to get all data
            all_data = self.admin_db.get_all_database_data()
            
            # Return the data as JSON response
            return all_data
            
        except Exception as e:
            custom_log(f"❌ Error in get_all_database_data endpoint: {e}", level="ERROR")
            return {"error": f"Failed to retrieve database data: {str(e)}"}, 500

    def get_user_by_email(self, email):
        """Get user by email with proper error handling."""
        try:
            return self.analytics_db.find_one("users", {"email": email})
        except Exception as e:
            self.logger.error(f"Error getting user by email: {e}")
            return None

    def create_user(self, username, email, hashed_password):
        """Create a new user with queued database operation."""
        try:
            user_data = {
                "username": username,
                "email": email,
                "password": hashed_password,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Insert user using queue system
            user_id = self.db_manager.insert("users", user_data)
            
            if user_id:
                return self.get_user_by_email(email)
            else:
                raise Exception("Failed to create user")
                
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            raise

    def delete_user(self, user_id):
        """Delete a user and all associated data with queued operations."""
        try:
            # Delete user data from all collections using queue system
            self.db_manager.delete("users", {"_id": user_id})
            self.db_manager.delete("user_sessions", {"user_id": user_id})
            self.db_manager.delete("user_tokens", {"user_id": user_id})
            
            # Invalidate any cached user data
            self._invalidate_caches(f"user:{user_id}")
            custom_log(f"✅ User {user_id} and associated data deleted")
        except Exception as e:
            self.logger.error(f"Error deleting user: {e}")
            raise

    def fetch_from_db(self, collection, query, as_dict=False):
        """Execute a query with queued operation and cache results in Redis."""
        try:
            # Validate query
            if not query or not isinstance(query, dict):
                raise ValueError("Invalid query format")
                
            # Create cache key based on query
            cache_key = f"query:{hash(str(query))}"
            
            # Try to get from Redis cache first
            try:
                cached_result = self.redis_manager.get(cache_key)
                if cached_result:
                    custom_log(f"✅ Retrieved query result from Redis cache")
                    return cached_result
            except Exception as e:
                self.logger.warning(f"Cache retrieval failed: {e}")
            
            # Execute query using queue system
            query_result = self.analytics_db.find(collection, query)
            
            # Cache the result
            try:
                self.redis_manager.set(cache_key, query_result, expire=300)  # Cache for 5 minutes
                custom_log(f"✅ Cached query result in Redis")
            except Exception as e:
                self.logger.warning(f"Cache storage failed: {e}")
            
            return query_result
            
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise

    def execute_query(self, collection, query, data=None):
        """Execute a write operation with queued operation and invalidate relevant caches."""
        try:
            if data:
                # Update operation using queue system
                modified_count = self.db_manager.update(collection, query, data)
            else:
                # Delete operation using queue system
                modified_count = self.db_manager.delete(collection, query)
            
            # Invalidate relevant caches
            self._invalidate_caches(collection)
            
            return modified_count
            
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            raise

    def _invalidate_caches(self, collection):
        """Invalidate relevant Redis caches based on the collection."""
        try:
            # Invalidate collection-specific caches
            pattern = f"query:*{collection}*"
            keys = self.redis_manager.redis.keys(pattern)
            for key in keys:
                self.redis_manager.delete(key)
            
            # Invalidate user data cache if users collection
            if collection == "users":
                pattern = "user:*"
                keys = self.redis_manager.redis.keys(pattern)
                for key in keys:
                    self.redis_manager.delete(key)
            
            custom_log("✅ Relevant caches invalidated")
        except Exception as e:
            self.logger.error(f"Error invalidating caches: {e}")
            raise

    def _create_session(self, user_id: int, username: str, email: str) -> dict:
        """Create a new session for a user with queued operation."""
        try:
            session_data = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'created_at': datetime.utcnow(),
                'expires_at': datetime.utcnow() + timedelta(seconds=self.session_timeout),
                'session_id': str(uuid.uuid4())
            }
            
            # Insert session using queue system
            session_id = self.db_manager.insert("user_sessions", session_data)
            
            if not session_id:
                raise Exception("Failed to create session")
            
            # Cache session in Redis
            self.redis_manager.set(
                f"session:{session_data['session_id']}", 
                session_data, 
                expire=self.session_timeout
            )
            
            return session_data
        except Exception as e:
            self.logger.error(f"Error creating session: {e}")
            raise

    def _remove_session(self, session_id: str, user_id: int) -> bool:
        """Remove a session for a user with queued operation."""
        try:
            # Delete session using queue system
            deleted_count = self.db_manager.delete("user_sessions", {"session_id": session_id, "user_id": user_id})
            
            if deleted_count == 0:
                self.logger.warning(f"Failed to remove session: No session found")
            
            # Remove from Redis cache
            self.redis_manager.delete(f"session:{session_id}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error removing session: {e}")
            return False

    def check_active_sessions(self, user_id: int) -> bool:
        """Check if user has active sessions with queued operation."""
        try:
            # Find sessions using queue system
            sessions = self.analytics_db.find("user_sessions", {"user_id": user_id})
            return len(sessions) > 0
        except Exception as e:
            self.logger.error(f"Error checking active sessions: {e}")
            return False

    def refresh_token_endpoint(self):
        """Endpoint to refresh authentication tokens."""
        try:
            # Get refresh token from request
            refresh_token = request.json.get('refresh_token') if request.json else None
            
            if not refresh_token:
                return {'error': 'Refresh token required'}, 400
            
            # Refresh the tokens
            result = self.refresh_user_tokens(refresh_token)
            
            if result.get('success'):
                return {
                    'access_token': result['access_token'],
                    'refresh_token': result['refresh_token'],
                    'expires_in': result['expires_in']
                }, 200
            else:
                return {'error': result.get('error', 'Token refresh failed')}, 401
                
        except Exception as e:
            self.logger.error(f"Error in refresh token endpoint: {e}")
            return {'error': 'Internal server error'}, 500

    def create_user_tokens(self, user_data):
        """Create JWT tokens for a user."""
        try:
            # Generate access token
            access_token_payload = {
                'user_id': user_data['_id'],
                'username': user_data['username'],
                'email': user_data['email'],
                'type': TokenType.ACCESS.value
            }
            
            access_token = self.jwt_manager.create_token(
                access_token_payload, 
                Config.JWT_ACCESS_TOKEN_EXPIRES
            )
            
            # Generate refresh token
            refresh_token_payload = {
                'user_id': user_data['_id'],
                'type': TokenType.REFRESH.value
            }
            
            refresh_token = self.jwt_manager.create_token(
                refresh_token_payload, 
                Config.JWT_REFRESH_TOKEN_EXPIRES
            )
            
            # Store tokens in Redis
            self.redis_manager.store_token('access', access_token, Config.JWT_ACCESS_TOKEN_EXPIRES)
            self.redis_manager.store_token('refresh', refresh_token, Config.JWT_REFRESH_TOKEN_EXPIRES)
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'expires_in': Config.JWT_ACCESS_TOKEN_EXPIRES,
                'token_type': 'Bearer'
            }
        except Exception as e:
            self.logger.error(f"Error creating user tokens: {e}")
            raise

    def validate_access_token(self, token):
        """Validate an access token."""
        try:
            # Validate token with JWT manager
            payload = self.jwt_manager.validate_token(token)
            
            # Check if token exists in Redis
            if not self.redis_manager.is_token_valid('access', token):
                return None
            
            return payload
        except Exception as e:
            self.logger.error(f"Error validating access token: {e}")
            return None

    def refresh_user_tokens(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh user tokens using a refresh token."""
        try:
            # Validate refresh token
            payload = self.jwt_manager.validate_token(refresh_token)
            if not payload or payload.get('type') != TokenType.REFRESH.value:
                return {'success': False, 'error': 'Invalid refresh token'}
            
            # Check if refresh token is valid in Redis
            if not self.redis_manager.is_token_valid('refresh', refresh_token):
                return {'success': False, 'error': 'Refresh token expired or revoked'}
            
            # Get user data
            user_id = payload.get('user_id')
            user_data = self.analytics_db.find_one("users", {"_id": user_id})
            
            if not user_data:
                return {'success': False, 'error': 'User not found'}
            
            # Revoke old tokens
            self.revoke_user_tokens(user_id)
            
            # Create new tokens
            new_tokens = self.create_user_tokens(user_data)
            
            return {
                'success': True,
                'access_token': new_tokens['access_token'],
                'refresh_token': new_tokens['refresh_token'],
                'expires_in': new_tokens['expires_in']
            }
            
        except Exception as e:
            self.logger.error(f"Error refreshing user tokens: {e}")
            return {'success': False, 'error': 'Token refresh failed'}

    def revoke_user_tokens(self, user_id: int) -> bool:
        """Revoke all tokens for a user."""
        try:
            # Get all user tokens from database
            user_tokens = self.analytics_db.find("user_tokens", {"user_id": user_id})
            
            # Revoke each token in Redis
            for token_data in user_tokens:
                if 'access_token' in token_data:
                    self.redis_manager.revoke_token('access', token_data['access_token'])
                if 'refresh_token' in token_data:
                    self.redis_manager.revoke_token('refresh', token_data['refresh_token'])
            
            # Remove token records from database
            self.db_manager.delete("user_tokens", {"user_id": user_id})
            
            custom_log(f"✅ All tokens revoked for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error revoking user tokens: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check for ConnectionAPI module."""
        health_status = {
            'module': self.module_name,
            'status': 'healthy',
            'details': {},
            'dependencies': []
        }
        
        try:
            # Check database connections
            db_healthy = self.db_manager.check_connection()
            health_status['details']['database'] = 'healthy' if db_healthy else 'unavailable'
            
            # Check Redis connection
            redis_healthy = self.redis_manager.ping()
            health_status['details']['redis'] = 'healthy' if redis_healthy else 'unhealthy'
            
            # Check JWT manager
            health_status['details']['jwt_manager'] = 'healthy'
            
            # Check API key manager
            api_key_health = self.api_key_manager.health_check()
            health_status['details']['api_key_manager'] = api_key_health['status']
            
            # Check database queue status
            try:
                queue_status = self.db_manager.get_queue_status()
                health_status['details']['database_queue'] = {
                    'queue_size': queue_status['queue_size'],
                    'worker_alive': queue_status['worker_alive'],
                    'queue_enabled': queue_status['queue_enabled'],
                    'pending_results': queue_status['pending_results']
                }
            except Exception as e:
                health_status['details']['database_queue'] = f'error: {str(e)}'
            
            # Overall status - app can run with limited functionality if only database is unavailable
            if not redis_healthy:
                health_status['status'] = 'unhealthy'
                health_status['details']['reason'] = 'Redis connection required for core functionality'
            elif not db_healthy:
                health_status['status'] = 'degraded'
                health_status['details']['reason'] = 'Database unavailable - running with limited functionality'
            else:
                health_status['status'] = 'healthy'
                
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['details']['error'] = str(e)
        
        return health_status

    def dispose(self):
        """Cleanup ConnectionAPI resources."""
        super().dispose()
        
        try:
            # Close database connections
            if hasattr(self.db_manager, 'close'):
                self.db_manager.close()
            if hasattr(self.analytics_db, 'close'):
                self.analytics_db.close()
            if hasattr(self.admin_db, 'close'):
                self.admin_db.close()
            
            # Close Redis connection
            if hasattr(self.redis_manager, 'close'):
                self.redis_manager.close()
                
            custom_log("ConnectionAPI module disposed successfully")
        except Exception as e:
            self.logger.error(f"Error disposing ConnectionAPI: {e}") 

    # API Key Management Methods
    def generate_api_key(self):
        """Generate a new API key for an external app."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['app_id', 'app_name']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }), 400
            
            app_id = data['app_id']
            app_name = data['app_name']
            permissions = data.get('permissions', ['read', 'write'])
            
            # Check if API key already exists for this app
            existing_api_key = self.api_key_manager.get_api_key_for_app(app_id)
            if existing_api_key:
                custom_log(f"✅ API key already exists for app: {app_name} ({app_id})")
                return jsonify({
                    'success': True,
                    'api_key': existing_api_key,
                    'app_id': app_id,
                    'app_name': app_name,
                    'permissions': permissions,
                    'message': 'API key already exists'
                }), 200
            
            # Generate new API key
            api_key = self.api_key_manager.generate_api_key(app_id, app_name, permissions)
            
            return jsonify({
                'success': True,
                'api_key': api_key,
                'app_id': app_id,
                'app_name': app_name,
                'permissions': permissions
            }), 201
            
        except Exception as e:
            custom_log(f"❌ Error generating API key: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to generate API key: {str(e)}'
            }), 500

    def validate_api_key(self):
        """Validate an API key."""
        try:
            data = request.get_json()
            
            if not data.get('api_key'):
                return jsonify({
                    'success': False,
                    'error': 'API key required'
                }), 400
            
            api_key = data['api_key']
            key_data = self.api_key_manager.validate_api_key(api_key)
            
            if key_data:
                return jsonify({
                    'success': True,
                    'valid': True,
                    'app_id': key_data.get('app_id'),
                    'app_name': key_data.get('app_name'),
                    'permissions': key_data.get('permissions'),
                    'is_active': key_data.get('is_active')
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'valid': False,
                    'error': 'Invalid or expired API key'
                }), 200
            
        except Exception as e:
            custom_log(f"❌ Error validating API key: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to validate API key: {str(e)}'
            }), 500

    def revoke_api_key(self):
        """Revoke an API key."""
        try:
            data = request.get_json()
            
            if not data.get('api_key'):
                return jsonify({
                    'success': False,
                    'error': 'API key required'
                }), 400
            
            api_key = data['api_key']
            success = self.api_key_manager.revoke_api_key(api_key)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'API key revoked successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to revoke API key'
                }), 400
            
        except Exception as e:
            custom_log(f"❌ Error revoking API key: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to revoke API key: {str(e)}'
            }), 500

    def list_api_keys(self):
        """List all API keys (admin only)."""
        try:
            keys = self.api_key_manager.list_api_keys()
            
            return jsonify({
                'success': True,
                'api_keys': keys,
                'count': len(keys)
            }), 200
            
        except Exception as e:
            custom_log(f"❌ Error listing API keys: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to list API keys: {str(e)}'
            }), 500

    def list_stored_api_keys(self):
        """List all API keys stored in secret files."""
        try:
            stored_keys = self.api_key_manager.list_stored_api_keys()
            
            return jsonify({
                'success': True,
                'stored_api_keys': stored_keys,
                'count': len(stored_keys)
            }), 200
            
        except Exception as e:
            custom_log(f"❌ Error listing stored API keys: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to list stored API keys: {str(e)}'
            }), 500 