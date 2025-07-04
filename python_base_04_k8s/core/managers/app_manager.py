# Plugin system removed - now using direct module management
# from core.managers.plugin_manager import PluginManager
from core.managers.service_manager import ServicesManager
from core.managers.hooks_manager import HooksManager
from core.managers.module_manager import ModuleManager
from core.managers.rate_limiter_manager import RateLimiterManager
from jinja2 import ChoiceLoader, FileSystemLoader
from tools.logger.custom_logging import custom_log, function_log, game_play_log, log_function_call
import os
from flask import request
import time
from utils.config.config import Config
from redis.exceptions import RedisError
from core.monitoring.metrics_collector import metrics_collector
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from core.managers.database_manager import DatabaseManager
from core.managers.redis_manager import RedisManager
from core.managers.state_manager import StateManager


class AppManager:
    def __init__(self):
        # Plugin system removed - ModuleManager is now primary orchestrator
        # self.plugin_manager = PluginManager()  # DEPRECATED
        self.services_manager = ServicesManager()
        self.hooks_manager = HooksManager()
        self.module_manager = ModuleManager()  # Primary orchestrator
        self.template_dirs = []  # List to track template directories
        self.flask_app = None  # Flask app reference
        self.logger = logging.getLogger(__name__)
        self.scheduler = None
        
        # Centralized managers - single instances for all modules
        self.db_manager = None
        self.analytics_db = None
        self.admin_db = None
        self.redis_manager = None
        self.rate_limiter_manager = None
        self.state_manager = None
        self._initialized = False

        custom_log("AppManager instance created.")

    def is_initialized(self):
        """Check if the AppManager is properly initialized."""
        return self._initialized

    def check_database_connection(self):
        """Check if the database connection is healthy."""
        try:
            if not self.db_manager:
                return False
            # Try to execute a simple query to check connection
            return self.db_manager.check_connection()
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False

    def check_redis_connection(self):
        """Check if the Redis connection is healthy."""
        try:
            if not self.redis_manager:
                return False
            # Try to execute a PING command
            return self.redis_manager.ping()
        except Exception as e:
            self.logger.error(f"Redis health check failed: {e}")
            return False

    def get_db_manager(self, role="read_write"):
        """Get the appropriate database manager instance."""
        if role == "read_write":
            return self.db_manager
        elif role == "read_only":
            return self.analytics_db
        elif role == "admin":
            return self.admin_db
        else:
            raise ValueError(f"Unknown database role: {role}")

    def get_redis_manager(self):
        """Get the Redis manager instance."""
        return self.redis_manager



    def get_state_manager(self):
        """Get the state manager instance."""
        return self.state_manager

    @log_function_call
    def initialize(self, app):
        """
        Initialize all components and plugins.
        """
        # Set the Flask app
        if not hasattr(app, "add_url_rule"):
            raise RuntimeError("AppManager requires a valid Flask app instance.")

        self.flask_app = app
        custom_log(f"AppManager initialized with Flask app: {self.flask_app}")

        # Initialize scheduler
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()

        # Initialize centralized database and Redis managers
        self.db_manager = DatabaseManager(role="read_write")
        self.analytics_db = DatabaseManager(role="read_only")
        self.admin_db = DatabaseManager(role="admin")
        self.redis_manager = RedisManager()
        self.rate_limiter_manager = RateLimiterManager()
        self.rate_limiter_manager.set_redis_manager(self.redis_manager)
        self.state_manager = StateManager(redis_manager=self.redis_manager, database_manager=self.db_manager)
        custom_log("✅ Centralized database, Redis, and State managers initialized")

        # Initialize services
        self.services_manager.initialize_services()

        # Initialize modules (replaces plugin system)
        custom_log("Initializing modules...")
        self.module_manager.initialize_modules(self)

        # Update the Jinja loader with template directories
        self._update_jinja_loader()

        # Initialize rate limiting middleware
        self._setup_rate_limiting()
        self._setup_rate_limit_headers()

        # Set up monitoring middleware
        self._setup_monitoring()
        

        
        # Mark as initialized
        self._initialized = True
        
        # Add module status endpoints
        self._setup_module_endpoints()

    def run(self, app, **kwargs):
        """Run the Flask application."""
        app.run(**kwargs)

    @log_function_call
    def get_plugins_path(self, return_url=False):
        """
        Retrieve the absolute path or the URL path for the plugins directory.

        :param return_url: If True, return the URL path for plugins; otherwise, return the absolute path.
        :return: String representing either the full path or the URL path.
        """
        try:
            # Get the absolute path of this file's directory (/app/core/)
            core_path = os.path.abspath(os.path.dirname(__file__))  
            
            # Move TWO levels up to reach /app/
            project_root = os.path.dirname(os.path.dirname(core_path))  

            # Now plugins should be correctly at /app/plugins
            plugins_dir = os.path.join(project_root, "plugins")  

            if return_url:
                if not self.flask_app:
                    raise RuntimeError("Flask app is not initialized in AppManager.")
                
                base_url = request.host_url.rstrip('/')
                return f"{base_url}/plugins"

            # Ensure the directory exists before returning
            if not os.path.exists(plugins_dir):
                custom_log(f"Warning: Plugins directory does not exist at {plugins_dir}")
                return None

            return plugins_dir
        except Exception as e:
            custom_log(f"Error retrieving plugins path: {e}")
            return None

    @log_function_call
    def register_template_dir(self, template_dir):
        """
        Register a template directory with the Flask app.
        :param template_dir: Path to the template directory.
        """
        if template_dir not in self.template_dirs:
            self.template_dirs.append(template_dir)
            custom_log(f"Template directory '{template_dir}' registered.")

    @log_function_call
    def _update_jinja_loader(self):
        """
        Update the Flask app's Jinja2 loader to include all registered template directories.
        """
        if not self.flask_app:
            raise RuntimeError("Flask app is not initialized in AppManager.")

        self.flask_app.jinja_loader = ChoiceLoader([
            FileSystemLoader(template_dir) for template_dir in self.template_dirs
        ])
        custom_log("Flask Jinja loader updated with registered template directories.")

    def _setup_rate_limiting(self):
        """Set up rate limiting middleware for the Flask app."""
        if not self.flask_app:
            return

        @self.flask_app.before_request
        def check_rate_limit():
            """Middleware to check rate limits before each request."""
            # Skip rate limiting for OPTIONS requests (CORS preflight)
            if request.method == 'OPTIONS':
                return None

            try:
                # Check all enabled rate limits
                limit_types = ['ip']  # Always check IP
                if self.rate_limiter_manager.config['user']['enabled']:
                    limit_types.append('user')
                if self.rate_limiter_manager.config['api_key']['enabled']:
                    limit_types.append('api_key')

                result = self.rate_limiter_manager.check_rate_limit(limit_types)
                
                if not result['allowed']:
                    # Log rate limit hit with details
                    exceeded_types = result['exceeded_types']
                    custom_log(
                        f"Rate limit exceeded for types: {exceeded_types}. "
                        f"IP: {request.remote_addr}, "
                        f"User: {self.rate_limiter_manager._get_user_id()}, "
                        f"API Key: {self.rate_limiter_manager._get_api_key()}",
                        level="WARNING"
                    )
                    
                    # Rate limit exceeded
                    from flask import make_response, jsonify
                    response = make_response(
                        jsonify({
                            'error': 'Rate limit exceeded',
                            'message': 'Too many requests',
                            'exceeded_types': exceeded_types,
                            'retry_after': max(result['reset_time'].values()) - int(time.time())
                        }),
                        429  # Too Many Requests
                    )
                    
                    # Add rate limit headers if enabled
                    if Config.RATE_LIMIT_HEADERS_ENABLED:
                        for limit_type in limit_types:
                            if limit_type in result['remaining']:
                                prefix = limit_type.upper()
                                response.headers[f'X-RateLimit-{prefix}-Limit'] = str(self.rate_limiter_manager.config[limit_type]['requests'])
                                response.headers[f'X-RateLimit-{prefix}-Remaining'] = str(result['remaining'][limit_type])
                                response.headers[f'X-RateLimit-{prefix}-Reset'] = str(result['reset_time'][limit_type])
                    
                    return response

                # Log rate limit warnings for monitoring
                for limit_type in limit_types:
                    if limit_type in result['remaining'] and result['remaining'][limit_type] < 10:
                        custom_log(
                            f"Rate limit warning for {limit_type}. "
                            f"Remaining: {result['remaining'][limit_type]}",
                            level="WARNING"
                        )

                # Store the result in request context for after_request
                request.rate_limit_result = result

            except RedisError as e:
                # Log Redis errors but allow the request to proceed
                custom_log(f"Redis error in rate limiting: {str(e)}", level="ERROR")
                return None
            except Exception as e:
                # Log other errors but allow the request to proceed
                custom_log(f"Error in rate limiting: {str(e)}", level="ERROR")
                return None

    def _setup_rate_limit_headers(self):
        """Set up rate limit headers middleware for the Flask app."""
        if not self.flask_app:
            return

        @self.flask_app.after_request
        def add_rate_limit_headers(response):
            try:
                if Config.RATE_LIMIT_HEADERS_ENABLED and hasattr(request, 'rate_limit_result'):
                    result = request.rate_limit_result
                    limit_types = ['ip']
                    if self.rate_limiter_manager.config['user']['enabled']:
                        limit_types.append('user')
                    if self.rate_limiter_manager.config['api_key']['enabled']:
                        limit_types.append('api_key')
                    
                    for limit_type in limit_types:
                        if limit_type in result['remaining']:
                            prefix = limit_type.upper()
                            response.headers[f'X-RateLimit-{prefix}-Limit'] = str(self.rate_limiter_manager.config[limit_type]['requests'])
                            response.headers[f'X-RateLimit-{prefix}-Remaining'] = str(result['remaining'][limit_type])
                            response.headers[f'X-RateLimit-{prefix}-Reset'] = str(result['reset_time'][limit_type])
            except Exception as e:
                custom_log(f"Error adding rate limit headers: {str(e)}", level="ERROR")
            return response
    
    def _setup_module_endpoints(self):
        """Set up module management and status endpoints."""
        if not self.flask_app:
            return

        @self.flask_app.route('/modules/status')
        def modules_status():
            """Get status of all modules."""
            try:
                status = self.module_manager.get_module_status()
                return status, 200
            except Exception as e:
                custom_log(f"Error getting module status: {e}")
                return {'error': 'Failed to get module status'}, 500

        @self.flask_app.route('/modules/<module_key>/health')
        def module_health(module_key):
            """Get health check for specific module."""
            try:
                module = self.module_manager.get_module(module_key)
                if not module:
                    return {'error': 'Module not found'}, 404
                
                health = module.health_check()
                return health, 200
            except Exception as e:
                custom_log(f"Error getting module health: {e}")
                return {'error': 'Failed to get module health'}, 500

        custom_log("Module management endpoints registered")

    @log_function_call
    def register_hook(self, hook_name):
        """
        Register a new hook by delegating to the HooksManager.
        :param hook_name: str - The name of the hook.
        """
        self.hooks_manager.register_hook(hook_name)
        custom_log(f"Hook '{hook_name}' registered via AppManager.")

    @log_function_call
    def register_hook_callback(self, hook_name, callback, priority=10, context=None):
        """
        Register a callback for a specific hook by delegating to the HooksManager.
        :param hook_name: str - The name of the hook.
        :param callback: callable - The callback function.
        :param priority: int - Priority of the callback (lower number = higher priority).
        :param context: str - Optional context for the callback.
        """
        self.hooks_manager.register_hook_callback(hook_name, callback, priority, context)
        callback_name = callback.__name__ if hasattr(callback, "__name__") else str(callback)
        custom_log(f"Callback '{callback_name}' registered for hook '{hook_name}' (priority: {priority}, context: {context}).")

    @log_function_call
    def trigger_hook(self, hook_name, data=None, context=None):
        """
        Trigger a specific hook by delegating to the HooksManager.
        :param hook_name: str - The name of the hook to trigger.
        :param data: Any - Data to pass to the callback.
        :param context: str - Optional context to filter callbacks.
        """
        custom_log(f"Triggering hook '{hook_name}' with data: {data} and context: {context}.")
        self.hooks_manager.trigger_hook(hook_name, data, context)

    def _setup_monitoring(self):
        """Set up monitoring middleware for the Flask app."""
        if not self.flask_app:
            return
            
        @self.flask_app.before_request
        def before_request():
            request.start_time = time.time()
            request.request_size = len(request.get_data())
            
        @self.flask_app.after_request
        def after_request(response):
            # Calculate request duration
            duration = time.time() - request.start_time
            
            # Track request metrics
            metrics_collector.track_request(
                method=request.method,
                endpoint=request.endpoint,
                status=response.status_code,
                duration=duration,
                size=request.request_size
            )
            
            return response
            
        # Set up periodic system metrics collection
        self._setup_system_metrics()
        
    def _setup_system_metrics(self):
        """Set up periodic collection of system metrics."""
        def update_system_metrics():
            try:
                # Update MongoDB connections
                if hasattr(self, 'db_manager'):
                    metrics_collector.update_mongodb_connections(
                        self.db_manager.get_connection_count()
                    )
                
                # Update Redis connections
                if hasattr(self, 'redis_manager'):
                    metrics_collector.update_redis_connections(
                        self.redis_manager.get_connection_count()
                    )
            except Exception as e:
                self.logger.error(f"Error updating system metrics: {e}")
        
        # Schedule periodic updates
        self.scheduler.add_job(
            update_system_metrics,
            'interval',
            seconds=15,
            id='system_metrics_update'
        )
