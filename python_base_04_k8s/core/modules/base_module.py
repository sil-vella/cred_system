from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from tools.logger.custom_logging import custom_log
import logging


class BaseModule(ABC):
    """
    Abstract base class for all application modules.
    Provides a standardized interface and common functionality.
    """
    
    def __init__(self, app_manager=None):
        """
        Initialize the base module.
        
        :param app_manager: Reference to the main AppManager instance
        """
        self.app_manager = app_manager
        self.app = None  # Flask app reference
        self.registered_routes = []
        self.dependencies = []
        self.module_name = self.__class__.__name__
        self.logger = logging.getLogger(f"modules.{self.module_name}")
        self._initialized = False
        
        custom_log(f"Module {self.module_name} created")
    
    @abstractmethod
    def initialize(self, app):
        """
        Initialize the module with the Flask application.
        This method must be implemented by all modules.
        
        :param app: Flask application instance
        """
        pass
    
    def register_routes(self):
        """
        Register module-specific routes with the Flask application.
        Override this method to add custom routes.
        """
        custom_log(f"No routes to register for module {self.module_name}")
    
    def configure(self):
        """
        Configure module-specific settings.
        Override this method for custom configuration.
        """
        custom_log(f"No configuration needed for module {self.module_name}")
    
    def dispose(self):
        """
        Cleanup module resources.
        Override this method for custom cleanup logic.
        """
        custom_log(f"Disposing module {self.module_name}")
        self._initialized = False
    
    def declare_dependencies(self) -> List[str]:
        """
        Return list of module names this module depends on.
        
        :return: List of module dependency names
        """
        return self.dependencies
    
    def is_initialized(self) -> bool:
        """
        Check if the module has been properly initialized.
        
        :return: True if initialized, False otherwise
        """
        return self._initialized
    
    def get_module_info(self) -> Dict[str, Any]:
        """
        Get information about this module.
        
        :return: Dictionary containing module metadata
        """
        return {
            'name': self.module_name,
            'initialized': self._initialized,
            'dependencies': self.dependencies,
            'routes_count': len(self.registered_routes),
            'routes': [route[0] if isinstance(route, tuple) else str(route) for route in self.registered_routes]
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the module.
        Override this method for custom health checks.
        
        :return: Dictionary containing health status
        """
        return {
            'module': self.module_name,
            'status': 'healthy' if self._initialized else 'not_initialized',
            'details': 'Module is functioning normally' if self._initialized else 'Module not initialized'
        }
    
    def _register_route_helper(self, route: str, view_func, methods: List[str] = None):
        """
        Helper method to register a route and track it.
        
        :param route: URL route pattern
        :param view_func: View function to handle the route
        :param methods: HTTP methods allowed for this route
        """
        if not self.app:
            raise RuntimeError(f"Cannot register route {route} - Flask app not initialized")
        
        if methods is None:
            methods = ["GET"]
        
        self.app.add_url_rule(route, view_func=view_func, methods=methods)
        self.registered_routes.append((route, view_func.__name__, methods))
        self.logger.info(f"Registered route: {route} with methods {methods}")
        custom_log(f"Module {self.module_name} registered route: {route}") 