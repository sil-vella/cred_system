from core.modules.base_module import BaseModule
from core.managers.database_manager import DatabaseManager
from core.managers.jwt_manager import JWTManager, TokenType
from core.managers.redis_manager import RedisManager
from tools.logger.custom_logging import custom_log
from flask import request, jsonify
from datetime import datetime
from typing import Dict, Any
from bson import ObjectId
import bcrypt
import re


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

    def initialize(self, app_manager):
        """Initialize the UserManagementModule with AppManager."""
        self.app_manager = app_manager
        self.app = app_manager.flask_app
        self.initialize_database()
        self.register_routes()
        self._initialized = True
        custom_log("UserManagementModule initialized")

    def register_routes(self):
        """Register user management routes."""
        # User CRUD operations
        self._register_route_helper("/users", self.create_user, methods=["POST"])
        self._register_route_helper("/users/<user_id>", self.get_user, methods=["GET"])
        self._register_route_helper("/users/<user_id>", self.update_user, methods=["PUT"])
        self._register_route_helper("/users/<user_id>", self.delete_user, methods=["DELETE"])
        self._register_route_helper("/users/search", self.search_users, methods=["POST"])
        
        # Authentication routes
        self._register_route_helper("/auth/register", self.register_user, methods=["POST"])
        self._register_route_helper("/auth/login", self.login_user, methods=["POST"])
        self._register_route_helper("/auth/logout", self.logout_user, methods=["POST"])
        self._register_route_helper("/auth/refresh", self.refresh_token, methods=["POST"])
        self._register_route_helper("/auth/me", self.get_current_user, methods=["GET"])
        
        # Test endpoint for debugging
        self._register_route_helper("/auth/test", self.test_debug, methods=["GET"])
        
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

    # Authentication Methods
    def register_user(self):
        """Register a new user account with authentication setup."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ["username", "email", "password"]
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }), 400
            
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")
            
            # Validate email format
            if not self._is_valid_email(email):
                return jsonify({
                    "success": False,
                    "error": "Invalid email format"
                }), 400
            
            # Validate password strength
            if not self._is_valid_password(password):
                return jsonify({
                    "success": False,
                    "error": "Password must be at least 8 characters long"
                }), 400
            
            # Check if user already exists
            existing_user = self.db_manager.find_one("users", {"email": email})
            if existing_user:
                return jsonify({
                    "success": False,
                    "error": "User with this email already exists"
                }), 409
            
            existing_username = self.db_manager.find_one("users", {"username": username})
            if existing_username:
                return jsonify({
                    "success": False,
                    "error": "Username already taken"
                }), 409
            
            # Hash password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # Prepare user data
            user_data = {
                'username': username,
                'email': email,
                'password': hashed_password.decode('utf-8'),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'active',
                'last_login': None,
                'login_count': 0
            }
            
            print(f"[DEBUG] Registering user: {email}")
            print(f"[DEBUG] Using db_manager: {self.db_manager}")
            print(f"[DEBUG] User data prepared: {user_data}")
            
            # Insert user using database manager
            user_id = self.db_manager.insert("users", user_data)
            
            print(f"[DEBUG] User inserted with ID: {user_id}")
            
            if not user_id:
                return jsonify({
                    "success": False,
                    "error": "Failed to create user account"
                }), 500
            
            # Create initial wallet for user
            wallet_data = {
                'user_id': user_id,
                'balance': 0.0,
                'currency': 'USD',
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
            
            wallet_id = self.db_manager.insert("wallets", wallet_data)
            
            # Remove password from response
            user_data.pop('password', None)
            user_data['_id'] = user_id
            
            custom_log(f"✅ User registered successfully: {username} ({email})")
            
            return jsonify({
                "success": True,
                "message": "User registered successfully",
                "data": {
                    "user": user_data,
                    "wallet_id": wallet_id
                }
            }), 201
            
        except Exception as e:
            custom_log(f"❌ Error registering user: {e}")
            return jsonify({
                "success": False,
                "error": "Internal server error"
            }), 500

    def login_user(self):
        """Authenticate user and return JWT tokens."""
        try:
            data = request.get_json()
            
            # Validate required fields
            if not data.get("email") or not data.get("password"):
                return jsonify({
                    "success": False,
                    "error": "Email and password are required"
                }), 400
            
            email = data.get("email")
            password = data.get("password")
            
            # Find user by email - use queue system
            custom_log(f"[DEBUG] Login attempt for {email}")
            custom_log(f"[DEBUG] Using db_manager: {self.db_manager}")
            custom_log(f"[DEBUG] Database available: {self.db_manager.available}")
            
            # Since email is a sensitive field (encrypted), we need to search differently
            # Get all users and decrypt their emails to find a match
            all_users = self.db_manager.find("users", {})
            custom_log(f"[DEBUG] Found {len(all_users)} users in database")
            
            user = None
            for u in all_users:
                if u.get('email') == email:
                    user = u
                    custom_log(f"[DEBUG] Found user with matching email: {email}")
                    break
            
            if not user:
                custom_log(f"[DEBUG] No user found for email: {email}")
                return jsonify({
                    "success": False,
                    "error": "Invalid email or password"
                }), 401
            
            # Check if user is active
            if user.get("status") != "active":
                return jsonify({
                    "success": False,
                    "error": "Account is not active"
                }), 401
            
            # Verify password
            stored_password = user.get("password", "")
            print(f"[DEBUG] Provided password: {password}")
            print(f"[DEBUG] Stored hash: {stored_password}")
            try:
                check_result = bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8'))
            except Exception as e:
                print(f"[DEBUG] bcrypt.checkpw error: {e}")
                check_result = False
            print(f"[DEBUG] bcrypt.checkpw result: {check_result}")
            if not check_result:
                return jsonify({
                    "success": False,
                    "error": "Invalid email or password"
                }), 401
            
            # Update last login and login count
            update_data = {
                "last_login": datetime.utcnow().isoformat(),
                "login_count": user.get("login_count", 0) + 1,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.db_manager.update("users", {"_id": user["_id"]}, update_data)
            
            # Create JWT tokens
            access_token_payload = {
                'user_id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'type': 'access'
            }
            
            refresh_token_payload = {
                'user_id': str(user['_id']),
                'type': 'refresh'
            }
            
            # Get JWT manager from app_manager
            jwt_manager = self.app_manager.jwt_manager
            access_token = jwt_manager.create_token(access_token_payload, TokenType.ACCESS)
            refresh_token = jwt_manager.create_token(refresh_token_payload, TokenType.REFRESH)
            
            # Remove password from response
            user.pop('password', None)
            
            custom_log(f"✅ User logged in successfully: {user['username']} ({email})")
            
            return jsonify({
                "success": True,
                "message": "Login successful",
                "data": {
                    "user": user,
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "Bearer",
                    "expires_in": 1800  # 30 minutes
                }
            }), 200
            
        except Exception as e:
            custom_log(f"❌ Error during login: {e}")
            return jsonify({
                "success": False,
                "error": "Internal server error"
            }), 500

    def logout_user(self):
        """Logout user and revoke tokens."""
        try:
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "error": "Missing or invalid authorization header"
                }), 401
            
            token = auth_header.split(' ')[1]
            
            # Get JWT manager from app_manager
            jwt_manager = self.app_manager.jwt_manager
            
            # Verify token
            payload = jwt_manager.verify_token(token, 'access')
            if not payload:
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired token"
                }), 401
            
            # Revoke the token
            success = jwt_manager.revoke_token(token)
            
            if success:
                custom_log(f"✅ User logged out successfully: {payload.get('username', 'unknown')}")
                return jsonify({
                    "success": True,
                    "message": "Logout successful"
                }), 200
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to logout"
                }), 500
            
        except Exception as e:
            custom_log(f"❌ Error during logout: {e}")
            return jsonify({
                "success": False,
                "error": "Internal server error"
            }), 500

    def refresh_token(self):
        """Refresh access token using refresh token."""
        try:
            data = request.get_json()
            
            if not data.get("refresh_token"):
                return jsonify({
                    "success": False,
                    "error": "Refresh token is required"
                }), 400
            
            refresh_token = data.get("refresh_token")
            
            # Get JWT manager from app_manager
            jwt_manager = self.app_manager.jwt_manager
            
            # Verify refresh token
            payload = jwt_manager.verify_token(refresh_token, 'refresh')
            if not payload:
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired refresh token"
                }), 401
            
            # Get user data
            user_id = payload.get("user_id")
            user = self.db_manager.find_one("users", {"_id": ObjectId(user_id)})
            
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 401
            
            # Create new access token
            access_token_payload = {
                'user_id': str(user['_id']),
                'username': user['username'],
                'email': user['email'],
                'type': 'access'
            }
            
            new_access_token = jwt_manager.create_token(access_token_payload, TokenType.ACCESS)
            
            # Remove password from response
            user.pop('password', None)
            
            custom_log(f"✅ Token refreshed successfully for user: {user['username']}")
            
            return jsonify({
                "success": True,
                "message": "Token refreshed successfully",
                "data": {
                    "user": user,
                    "access_token": new_access_token,
                    "token_type": "Bearer",
                    "expires_in": 1800  # 30 minutes
                }
            }), 200
            
        except Exception as e:
            custom_log(f"❌ Error refreshing token: {e}")
            return jsonify({
                "success": False,
                "error": "Internal server error"
            }), 500

    def get_current_user(self):
        """Get current user information from token."""
        try:
            # Get token from Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "error": "Missing or invalid authorization header"
                }), 401
            
            token = auth_header.split(' ')[1]
            
            # Get JWT manager from app_manager
            jwt_manager = self.app_manager.jwt_manager
            
            # Verify token
            payload = jwt_manager.verify_token(token, 'access')
            if not payload:
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired token"
                }), 401
            
            # Get user data
            user_id = payload.get("user_id")
            user = self.db_manager.find_one("users", {"_id": ObjectId(user_id)})
            
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 401
            
            # Get user's wallet
            wallet = self.db_manager.find_one("wallets", {"user_id": user_id})
            
            # Remove password from response
            user.pop('password', None)
            
            return jsonify({
                "success": True,
                "data": {
                    "user": user,
                    "wallet": wallet
                }
            }), 200
            
        except Exception as e:
            custom_log(f"❌ Error getting current user: {e}")
            return jsonify({
                "success": False,
                "error": "Internal server error"
            }), 500

    def _is_valid_email(self, email: str) -> bool:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _is_valid_password(self, password: str) -> bool:
        """Validate password strength."""
        return len(password) >= 8

    def test_debug(self):
        """Test endpoint to verify debug logging works."""
        print("[DEBUG] Test endpoint called!")
        print(f"[DEBUG] Database manager: {self.db_manager}")
        print(f"[DEBUG] Analytics DB: {self.analytics_db}")
        return jsonify({"message": "Debug test successful"}), 200

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