"""
Login Module - Handles user authentication, registration, and session management
"""

import os
import bcrypt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from flask import request, jsonify, make_response
from bson import ObjectId

from core.modules.base_module import BaseModule
from core.managers.jwt_manager import JWTManager, TokenType
from tools.logger.custom_logging import custom_log
from utils.config.config import Config


class LoginModule(BaseModule):
    """Login Module - Handles user authentication and session management"""
    
    NAME = "login"
    DEPENDENCIES = ["connection_api", "user_management"]
    
    def __init__(self, app_manager=None):
        """Initialize the LoginModule."""
        super().__init__(app_manager)
        
        # Set dependencies
        self.dependencies = ["connection_api", "user_management"]
        
        # Initialize JWT manager
        self.jwt_manager = None
        
        # Initialize database managers
        self.db_manager = None
        self.analytics_db = None
        
        # Ensure user_management attribute always exists
        self.user_management = None
        
        custom_log("LoginModule created")

    def initialize(self, app_manager) -> bool:
        """Initialize the LoginModule with dependencies and resources."""
        try:
            self.app_manager = app_manager
            self.app = app_manager.flask_app
            
            # Get JWT manager from app_manager
            self.jwt_manager = app_manager.jwt_manager
            if not self.jwt_manager:
                custom_log("❌ JWT Manager not available for LoginModule")
                return False
            
            # Get database managers
            self.db_manager = app_manager.db_manager
            self.analytics_db = app_manager.analytics_db
            
            if not self.db_manager or not self.analytics_db:
                custom_log("❌ Database managers not available for LoginModule")
                return False
            
            # Get user management module
            self.user_management = app_manager.module_manager.get_module("user_management")
            if not self.user_management:
                custom_log("❌ User management module not available for LoginModule")
                return False
            
            # Register routes
            self.register_routes(self.app)
            
            custom_log("✅ LoginModule initialized successfully")
            return True
            
        except Exception as e:
            custom_log(f"❌ Error initializing LoginModule: {e}")
            return False

    def register_routes(self, app):
        """Register all login-related routes."""
        custom_log("Registering LoginModule routes...")
        
        # Register authentication routes
        self._register_route_helper("/auth/register", self.register_user, methods=["POST"])
        self._register_route_helper("/auth/login", self.login_user, methods=["POST"])
        self._register_route_helper("/auth/logout", self.logout_user, methods=["POST"])
        self._register_route_helper("/auth/refresh", self.refresh_token, methods=["POST"])
        self._register_route_helper("/auth/me", self.get_current_user, methods=["GET"])
        
        custom_log(f"LoginModule registered {len(self.registered_routes)} routes")

    def health_check(self) -> dict:
        """Return current health status of the LoginModule."""
        try:
            # Check JWT manager
            jwt_healthy = self.jwt_manager is not None
            
            # Check database connection
            db_healthy = self.db_manager.available if self.db_manager else False
            
            # Check user management module
            user_mgmt_healthy = self.user_management is not None
            
            # Check dependencies
            dependencies_healthy = all([
                jwt_healthy,
                db_healthy,
                user_mgmt_healthy
            ])
            
            return {
                "status": "healthy" if dependencies_healthy else "unhealthy",
                "module": self.NAME,
                "jwt_manager": jwt_healthy,
                "database_connection": db_healthy,
                "user_management_module": user_mgmt_healthy,
                "dependencies": {
                    "connection_api": db_healthy,
                    "user_management": user_mgmt_healthy
                },
                "last_check": datetime.utcnow().isoformat(),
                "uptime": self._get_uptime()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "module": self.NAME,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }

    def register_user(self):
        """Register a new user account."""
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
            existing_user = self.analytics_db.find_one("users", {"email": email})
            if existing_user:
                return jsonify({
                    "success": False,
                    "error": "User with this email already exists"
                }), 409
            
            existing_username = self.analytics_db.find_one("users", {"username": username})
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
            
            # Insert user using database manager
            user_id = self.db_manager.insert("users", user_data)
            
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
            
            # Find user by email
            user = self.analytics_db.find_one("users", {"email": email})
            if not user:
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
            if not bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
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
                'type': TokenType.ACCESS.value
            }
            
            refresh_token_payload = {
                'user_id': str(user['_id']),
                'type': TokenType.REFRESH.value
            }
            
            access_token = self.jwt_manager.create_token(access_token_payload, TokenType.ACCESS)
            refresh_token = self.jwt_manager.create_token(refresh_token_payload, TokenType.REFRESH)
            
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
            
            # Verify token
            payload = self.jwt_manager.verify_token(token, TokenType.ACCESS)
            if not payload:
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired token"
                }), 401
            
            # Revoke the token
            success = self.jwt_manager.revoke_token(token)
            
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
            
            # Verify refresh token
            payload = self.jwt_manager.verify_token(refresh_token, TokenType.REFRESH)
            if not payload:
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired refresh token"
                }), 401
            
            # Get user data
            user_id = payload.get("user_id")
            user = self.analytics_db.find_one("users", {"_id": ObjectId(user_id)})
            
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
                'type': TokenType.ACCESS.value
            }
            
            new_access_token = self.jwt_manager.create_token(access_token_payload, TokenType.ACCESS)
            
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
            
            # Verify token
            payload = self.jwt_manager.verify_token(token, TokenType.ACCESS)
            if not payload:
                return jsonify({
                    "success": False,
                    "error": "Invalid or expired token"
                }), 401
            
            # Get user data
            user_id = payload.get("user_id")
            user = self.analytics_db.find_one("users", {"_id": ObjectId(user_id)})
            
            if not user:
                return jsonify({
                    "success": False,
                    "error": "User not found"
                }), 401
            
            # Get user's wallet
            wallet = self.analytics_db.find_one("wallets", {"user_id": user_id})
            
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
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def _is_valid_password(self, password: str) -> bool:
        """Validate password strength."""
        return len(password) >= 8

    def _get_uptime(self) -> str:
        """Get module uptime."""
        if hasattr(self, '_start_time'):
            uptime = datetime.utcnow() - self._start_time
            return str(uptime)
        return "Unknown" 