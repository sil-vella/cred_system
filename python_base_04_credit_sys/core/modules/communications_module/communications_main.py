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


class CommunicationsModule(BaseModule):
    def __init__(self, app_manager=None):
        """Initialize the CommunicationsModule module with Redis and database connections."""
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

        custom_log(f"CommunicationsModule module created with shared managers")

    def initialize(self, app_manager):
        """Initialize the CommunicationsModule with AppManager."""
        self.app_manager = app_manager
        self.app = app_manager.flask_app
        custom_log(f"CommunicationsModule initialized with AppManager")
        
        # Ensure collections exist in the database
        self.initialize_database()
        
        # Register routes
        self.register_routes()
        
        # Mark as initialized
        self._initialized = True

    def register_routes(self):
        """Register all CommunicationsModule routes."""
        custom_log("Registering CommunicationsModule routes...")
        
        # Register core routes
        self._register_route_helper("/", self.home, methods=["GET"])
        self._register_route_helper("/get-db-data", self.get_all_database_data, methods=["GET"])
        
        # Register API key management routes directly from API Key Manager
        self._register_route_helper("/api-keys/generate", self.api_key_manager.generate_api_key_endpoint, methods=["POST"])
        self._register_route_helper("/api-keys/validate", self.api_key_manager.validate_api_key_endpoint, methods=["POST"])
        self._register_route_helper("/api-keys/revoke", self.api_key_manager.revoke_api_key_endpoint, methods=["POST"])
        self._register_route_helper("/api-keys/list", self.api_key_manager.list_api_keys_endpoint, methods=["GET"])
        self._register_route_helper("/api-keys/stored", self.api_key_manager.list_stored_api_keys_endpoint, methods=["GET"])
        
        custom_log(f"CommunicationsModule registered {len(self.registered_routes)} routes")

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
        return {"message": "CommunicationsModule module is running", "version": "2.0", "module": "communications_module"}

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

    def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check for CommunicationsModule module."""
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
        """Cleanup CommunicationsModule resources."""
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
                
            custom_log("CommunicationsModule module disposed successfully")
        except Exception as e:
            self.logger.error(f"Error disposing CommunicationsModule: {e}") 

 