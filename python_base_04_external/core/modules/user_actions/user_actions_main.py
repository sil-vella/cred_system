from core.modules.base_module import BaseModule
from tools.logger.custom_logging import custom_log
from typing import Dict, Any
import yaml
import os
from flask import request, jsonify


class UserActionsModule(BaseModule):
    def __init__(self, app_manager=None):
        """Initialize the UserActionsModule."""
        super().__init__(app_manager)
        
        # Set dependencies
        self.dependencies = ["user_management"]
        
        # Path to actions YAML file
        self.actions_file = os.path.join(os.path.dirname(__file__), "declarations", "actions.yaml")
        
        # Load actions configuration
        self.actions_config = self._load_actions_config()
        
        custom_log("UserActionsModule created")

    def initialize(self, app_manager):
        """Initialize the UserActionsModule with AppManager."""
        self.app_manager = app_manager
        self.app = app_manager.flask_app
        self.register_routes()
        self._initialized = True
        custom_log("UserActionsModule initialized")

    def register_routes(self):
        """Register user actions routes."""
        # Generic action endpoint that processes YAML-defined actions
        self._register_route_helper("/actions/<action_name>", self.execute_action, methods=["POST"])
        self._register_route_helper("/actions", self.list_actions, methods=["GET"])
        
        custom_log(f"UserActionsModule registered {len(self.registered_routes)} routes")

    def execute_action(self, action_name: str):
        """Execute a user action based on YAML configuration."""
        try:
            # Get action configuration
            action_config = self.actions_config.get('actions', {}).get(action_name)
            
            if not action_config:
                return jsonify({
                    'error': f'Action "{action_name}" not found',
                    'available_actions': list(self.actions_config.get('actions', {}).keys())
                }), 404
            
            # Get request data
            request_data = request.get_json() or {}
            
            # Validate required parameters
            required_params = action_config.get('required_params', [])
            missing_params = [param for param in required_params if param not in request_data]
            
            if missing_params:
                return jsonify({
                    'error': f'Missing required parameters: {missing_params}',
                    'required_params': required_params,
                    'optional_params': action_config.get('optional_params', [])
                }), 400
            
            # Execute action based on type
            action_type = action_config.get('type', 'function')
            result = self._execute_action_by_type(action_type, action_config, request_data)
            
            return jsonify({
                'success': True,
                'action': action_name,
                'result': result
            }), 200

        except Exception as e:
            custom_log(f"Error executing action {action_name}: {e}")
            return jsonify({'error': f'Failed to execute action: {str(e)}'}), 500

    def _execute_action_by_type(self, action_type: str, action_config: Dict, request_data: Dict) -> Any:
        """Execute action based on its type."""
        if action_type == "function":
            return self._execute_function_action(action_config, request_data)
        elif action_type == "database":
            return self._execute_database_action(action_config, request_data)
        elif action_type == "external_api":
            return self._execute_external_api_action(action_config, request_data)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    def _execute_function_action(self, action_config: Dict, request_data: Dict) -> Any:
        """Execute a function-based action."""
        function_name = action_config.get("function")
        
        # Note: User-specific functions have been removed as they should be handled by credit system
        # Only generic utility functions should remain here
        if function_name == "validate_user_permissions":
            return self._validate_user_permissions(request_data)
        else:
            raise ValueError(f"Unknown function: {function_name}")

    def _execute_database_action(self, action_config: Dict, request_data: Dict) -> Any:
        """Execute a database action."""
        operation = action_config.get("operation")
        collection = action_config.get("collection")
        query = request_data.get("query", {})
        
        if operation == "find":
            # Note: User-specific database operations should be forwarded to credit system
            # This is kept for non-user collections only
            if collection == "users":
                raise ValueError("User operations should be handled by credit system")
            
            # For non-user collections, use local database
            if self.app_manager:
                db_manager = self.app_manager.get_db_manager(role="read_only")
                return db_manager.find(collection, query)
            else:
                raise ValueError("Database manager not available")
        
        else:
            raise ValueError(f"Unknown database operation: {operation}")

    def _execute_external_api_action(self, action_config: Dict, request_data: Dict) -> Any:
        """Execute an external API action."""
        import requests
        
        url = action_config.get("url")
        method = action_config.get("method", "GET")
        
        if not url:
            raise ValueError("External API URL not configured")
        
        # Make request to external API
        response = requests.request(
            method=method,
            url=url,
            json=request_data,
            timeout=30
        )
        
        return {
            'status_code': response.status_code,
            'response': response.json() if response.content else {}
        }

    def _validate_user_permissions(self, request_data: Dict) -> Dict:
        """Validate user permissions (generic utility function)."""
        try:
            user_id = request_data.get("user_id")
            permission = request_data.get("permission")
            resource_id = request_data.get("resource_id")
            
            if not user_id or not permission:
                return {
                    "valid": False,
                    "error": "User ID and permission are required"
                }
            
            # This is a generic permission validation framework
            # Specific user permission logic should be handled by credit system
            return {
                "valid": True,
                "user_id": user_id,
                "permission": permission,
                "resource_id": resource_id,
                "message": "Permission validation framework available"
            }
            
        except Exception as e:
            custom_log(f"Error validating user permissions: {e}")
            return {
                "valid": False,
                "error": f"Permission validation error: {str(e)}"
            }

    def list_actions(self):
        """List all available actions."""
        try:
            actions = self.actions_config.get('actions', {})
            
            # Format actions for display
            formatted_actions = {}
            for action_name, action_config in actions.items():
                formatted_actions[action_name] = {
                    'description': action_config.get('description', ''),
                    'type': action_config.get('type', ''),
                    'required_params': action_config.get('required_params', []),
                    'optional_params': action_config.get('optional_params', []),
                    'examples': action_config.get('examples', [])
                }
            
            return jsonify({
                'success': True,
                'actions': formatted_actions,
                'total_actions': len(formatted_actions)
            }), 200
            
        except Exception as e:
            custom_log(f"Error listing actions: {e}")
            return jsonify({'error': f'Failed to list actions: {str(e)}'}), 500

    def _load_actions_config(self) -> Dict[str, Any]:
        """Load actions configuration from YAML file."""
        try:
            if os.path.exists(self.actions_file):
                with open(self.actions_file, 'r') as f:
                    config = yaml.safe_load(f)
                custom_log(f"✅ Loaded actions configuration from {self.actions_file}")
                return config
            else:
                custom_log(f"⚠️ Actions configuration file not found: {self.actions_file}")
                return {'actions': {}}
                
        except Exception as e:
            custom_log(f"❌ Error loading actions configuration: {e}")
            return {'actions': {}}

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for UserActionsModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        
        # Add actions configuration status
        try:
            actions_count = len(self.actions_config.get('actions', {}))
            health_status['details'] = {
                'actions_configured': actions_count,
                'config_file': self.actions_file,
                'config_loaded': bool(self.actions_config.get('actions'))
            }
        except Exception as e:
            health_status['details'] = {
                'error': f'Failed to check actions config: {str(e)}'
            }
        
        return health_status 