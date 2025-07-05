from flask import Flask
from flask_cors import CORS
from core.managers.app_manager import AppManager
import sys
import os
from core.metrics import init_metrics
from utils.config.config import Config
from tools.logger.custom_logging import custom_log

sys.path.append(os.path.abspath(os.path.dirname(__file__)))


# Initialize the AppManager
app_manager = AppManager()

# Initialize the Flask app
app = Flask(__name__)

# Enable Cross-Origin Resource Sharing (CORS)
CORS(app)

# Initialize metrics
metrics = init_metrics(app)

# Initialize the AppManager and pass the app for plugin registration
app_manager.initialize(app)

# Additional app-level configurations
app.config["DEBUG"] = Config.DEBUG

@app.route('/health')
def health_check():
    """Health check endpoint for Kubernetes liveness and readiness probes"""
    custom_log("Health check endpoint called")
    try:
        # Check if the application is properly initialized
        if not app_manager.is_initialized():
            return {'status': 'unhealthy', 'reason': 'App manager not initialized'}, 503
            
        # Check database connection
        if not app_manager.check_database_connection():
            return {'status': 'unhealthy', 'reason': 'Database connection failed'}, 503
            
        # Check Redis connection
        if not app_manager.check_redis_connection():
            return {'status': 'unhealthy', 'reason': 'Redis connection failed'}, 503
        
        # Check state manager status
        state_manager_health = app_manager.state_manager.health_check()
        if state_manager_health.get('status') != 'healthy':
            return {'status': 'unhealthy', 'reason': 'State manager unhealthy'}, 503
        
        # Check module status
        module_status = app_manager.module_manager.get_module_status()
        unhealthy_modules = []
        
        for module_key, module_info in module_status.get('modules', {}).items():
            if module_info.get('health', {}).get('status') != 'healthy':
                unhealthy_modules.append(module_key)
        
        if unhealthy_modules:
            return {
                'status': 'degraded', 
                'reason': f'Unhealthy modules: {unhealthy_modules}',
                'module_status': module_status
            }, 200  # Still return 200 for degraded but functional
            
        return {
            'status': 'healthy',
            'modules_initialized': module_status.get('initialized_modules', 0),
            'total_modules': module_status.get('total_modules', 0),
            'state_manager': state_manager_health
        }, 200
    except Exception as e:
        return {'status': 'unhealthy', 'reason': str(e)}, 503

if __name__ == "__main__":
    # Use environment variables for host and port
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5001))
    app_manager.run(app, host=host, port=port)
# Test comment from watcher - Wed Jul  2 18:40:27 CEST 2025
