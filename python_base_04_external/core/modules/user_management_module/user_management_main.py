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
import requests
from utils.config.config import Config


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
        
        # Credit system configuration
        self.credit_system_url = Config.CREDIT_SYSTEM_URL
        # Use dynamic API key getter that generates if empty
        self.api_key = Config.get_credit_system_api_key()
        
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
        """Register wildcard routes that capture all user-related requests."""
        # Only 2 wildcard routes that capture everything
        self._register_route_helper("/users/<path:subpath>", self.forward_user_request, methods=["GET", "POST", "PUT", "DELETE"])
        self._register_route_helper("/auth/users/<path:subpath>", self.forward_user_request, methods=["GET", "POST", "PUT", "DELETE"])
        
        # Test endpoint for debugging
        self._register_route_helper("/auth/test", self.test_debug, methods=["GET"])
        
        custom_log(f"UserManagementModule registered 2 wildcard routes for user forwarding")

    def forward_user_request(self, subpath=None):
        """Forward user management requests to credit system with API key."""
        try:
            # Get the current request path and method
            path = request.path
            method = request.method
            
            # Build the target path on credit system
            # If it's /users/search, forward to /users/search
            # If it's /auth/users/login, forward to /auth/login
            target_path = self._build_credit_system_path(path)
            
            # Prepare headers with API key
            headers = {
                'X-API-Key': self.api_key,
                'Content-Type': 'application/json'
            }
            
            # Forward any existing Authorization header (JWT tokens)
            auth_header = request.headers.get('Authorization')
            if auth_header:
                headers['Authorization'] = auth_header
            
            # Prepare request data
            data = None
            if method in ['POST', 'PUT']:
                data = request.get_json()
            
            # Build target URL
            target_url = f"{self.credit_system_url}{target_path}"
            
            custom_log(f"🔄 Forwarding {method} request to credit system: {target_url}")
            custom_log(f"🔄 Original path: {path}")
            custom_log(f"🔄 Target path: {target_path}")
            custom_log(f"🔄 Headers: {headers}")
            if data:
                custom_log(f"🔄 Data: {data}")
            
            # Make request to credit system
            response = requests.request(
                method=method,
                url=target_url,
                headers=headers,
                json=data if data else None,
                timeout=30
            )
            
            # Forward the response back to the client
            response_data = response.json() if response.content else {}
            status_code = response.status_code
            
            custom_log(f"✅ Credit system response: {status_code} - {response_data}")
            
            return jsonify(response_data), status_code
            
        except requests.exceptions.RequestException as e:
            custom_log(f"❌ Error forwarding request to credit system: {e}")
            return jsonify({
                "success": False,
                "error": "Credit system unavailable",
                "message": "Unable to connect to credit system"
            }), 503
            
        except Exception as e:
            custom_log(f"❌ Unexpected error in forward_user_request: {e}")
            return jsonify({
                "success": False,
                "error": "Internal server error",
                "message": "Failed to process request"
            }), 500

    def _build_credit_system_path(self, external_path):
        """Build the target path for credit system based on external app path."""
        # Remove leading slash and split path
        path_parts = external_path.strip('/').split('/')
        
        if len(path_parts) < 2:
            return external_path  # Return as-is if invalid path
        
        # Handle /users/* paths
        if path_parts[0] == 'users':
            # Forward /users/search to /users/search
            # Forward /users/123 to /users/123
            # Forward /users/123/profile to /users/123/profile
            return f"/{'/'.join(path_parts)}"
        
        # Handle /auth/users/* paths
        elif path_parts[0] == 'auth' and path_parts[1] == 'users':
            # Forward /auth/users/login to /auth/login
            # Forward /auth/users/logout to /auth/logout
            # Forward /auth/users/123 to /auth/123
            # Forward /auth/users/me to /auth/me
            if len(path_parts) == 3:
                # /auth/users/login -> /auth/login
                return f"/auth/{path_parts[2]}"
            elif len(path_parts) == 4:
                # /auth/users/123/profile -> /auth/123/profile
                return f"/auth/{path_parts[2]}/{path_parts[3]}"
            else:
                # Fallback for complex paths
                return f"/auth/{'/'.join(path_parts[2:])}"
        
        # Return original path if no mapping found
        return external_path

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

    def test_debug(self):
        """Test endpoint to verify debug logging works."""
        print("[DEBUG] Test endpoint called!")
        print(f"[DEBUG] Database manager: {self.db_manager}")
        print(f"[DEBUG] Analytics DB: {self.analytics_db}")
        print(f"[DEBUG] Credit system URL: {self.credit_system_url}")
        print(f"[DEBUG] API key configured: {'Yes' if self.api_key else 'No'}")
        return jsonify({
            "message": "Debug test successful",
            "credit_system_url": self.credit_system_url,
            "api_key_configured": bool(self.api_key)
        }), 200

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for UserManagementModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        
        # Add credit system connection status
        try:
            # Test connection to credit system
            response = requests.get(
                f"{self.credit_system_url}/health",
                headers={'X-API-Key': self.api_key},
                timeout=5
            )
            credit_system_status = "healthy" if response.status_code == 200 else "unhealthy"
        except Exception as e:
            credit_system_status = f"error: {str(e)}"
        
        # Add database queue status
        try:
            queue_status = self.db_manager.get_queue_status()
            health_status['details'] = {
                'database_queue': {
                    'queue_size': queue_status['queue_size'],
                    'worker_alive': queue_status['worker_alive'],
                    'queue_enabled': queue_status['queue_enabled'],
                    'pending_results': queue_status['pending_results']
                },
                'credit_system_connection': {
                    'status': credit_system_status,
                    'url': self.credit_system_url,
                    'api_key_configured': bool(self.api_key)
                }
            }
        except Exception as e:
            health_status['details'] = {
                'database_queue': f'error: {str(e)}',
                'credit_system_connection': {
                    'status': credit_system_status,
                    'url': self.credit_system_url,
                    'api_key_configured': bool(self.api_key)
                }
            }
        
        return health_status 