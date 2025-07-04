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

    def initialize(self, app):
        """Initialize the UserActionsModule with Flask app."""
        self.app = app
        self.register_routes()
        self._initialized = True
        custom_log("UserActionsModule initialized")

    def register_routes(self):
        """Register user actions routes."""
        # Generic action endpoint that processes YAML-defined actions
        self._register_route_helper("/actions/<action_name>", self.execute_action, methods=["POST"])
        self._register_route_helper("/actions", self.list_actions, methods=["GET"])
        
        custom_log(f"UserActionsModule registered {len(self.registered_routes)} routes")

    def _load_actions_config(self) -> Dict[str, Any]:
        """Load actions configuration from YAML file."""
        try:
            if os.path.exists(self.actions_file):
                with open(self.actions_file, 'r') as file:
                    config = yaml.safe_load(file)
                    custom_log(f"Loaded {len(config.get('actions', {}))} actions from {self.actions_file}")
                    return config
            else:
                custom_log(f"Actions file not found: {self.actions_file}")
                return {"actions": {}}
        except Exception as e:
            custom_log(f"Error loading actions config: {e}")
            return {"actions": {}}

    def execute_action(self, action_name: str):
        """Execute an action based on YAML configuration."""
        try:
            # Get action configuration
            action_config = self.actions_config.get("actions", {}).get(action_name)
            if not action_config:
                return jsonify({'error': f'Action "{action_name}" not found'}), 404

            # Get request data (named arguments)
            request_data = request.get_json() or {}
            
            # Validate required parameters
            required_params = action_config.get("required_params", [])
            missing_params = [param for param in required_params if param not in request_data]
            if missing_params:
                return jsonify({
                    'error': f'Missing required parameters: {missing_params}',
                    'required_params': required_params
                }), 400

            # Execute the action based on type
            action_type = action_config.get("type", "function")
            result = self._execute_action_by_type(action_type, action_config, request_data)
            
            return jsonify({
                'action': action_name,
                'result': result,
                'status': 'success'
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
        if function_name == "get_user_profile":
            return self._get_user_profile(request_data)
        elif function_name == "update_user_preferences":
            return self._update_user_preferences(request_data)
        elif function_name == "validate_user_permissions":
            return self._validate_user_permissions(request_data)
        else:
            raise ValueError(f"Unknown function: {function_name}")

    def _execute_database_action(self, action_config: Dict, request_data: Dict) -> Any:
        """Execute a database-based action."""
        # This would integrate with your database manager
        operation = action_config.get("operation")
        collection = action_config.get("collection")
        
        # For now, return a placeholder
        return {
            "operation": operation,
            "collection": collection,
            "data": request_data,
            "status": "database_operation_placeholder"
        }

    def _execute_external_api_action(self, action_config: Dict, request_data: Dict) -> Any:
        """Execute an external API action."""
        # This would make HTTP requests to external services
        url = action_config.get("url")
        method = action_config.get("method", "GET")
        
        return {
            "url": url,
            "method": method,
            "data": request_data,
            "status": "external_api_placeholder"
        }

    def _get_user_profile(self, request_data: Dict) -> Dict:
        """Example function action: Get user profile."""
        user_id = request_data.get("user_id")
        return {
            "user_id": user_id,
            "profile": {
                "username": f"user_{user_id}",
                "email": f"user_{user_id}@example.com",
                "preferences": {"theme": "dark", "notifications": True}
            }
        }

    def _update_user_preferences(self, request_data: Dict) -> Dict:
        """Example function action: Update user preferences."""
        user_id = request_data.get("user_id")
        preferences = request_data.get("preferences", {})
        return {
            "user_id": user_id,
            "updated_preferences": preferences,
            "status": "updated"
        }

    def _validate_user_permissions(self, request_data: Dict) -> Dict:
        """Example function action: Validate user permissions."""
        user_id = request_data.get("user_id")
        permission = request_data.get("permission")
        resource_id = request_data.get("resource_id")
        
        # Mock permission validation logic
        has_permission = permission in ["read", "write", "admin"]
        
        return {
            "user_id": user_id,
            "permission": permission,
            "resource_id": resource_id,
            "has_permission": has_permission,
            "status": "validated"
        }

    def list_actions(self):
        """List all available actions."""
        try:
            actions = self.actions_config.get("actions", {})
            action_list = []
            
            for action_name, action_config in actions.items():
                action_info = {
                    "name": action_name,
                    "description": action_config.get("description", ""),
                    "type": action_config.get("type", "function"),
                    "required_params": action_config.get("required_params", []),
                    "optional_params": action_config.get("optional_params", [])
                }
                action_list.append(action_info)
            
            return jsonify({
                "actions": action_list,
                "total": len(action_list)
            }), 200
            
        except Exception as e:
            custom_log(f"Error listing actions: {e}")
            return jsonify({'error': 'Failed to list actions'}), 500

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for UserActionsModule."""
        health_status = super().health_check()
        health_status['dependencies'] = self.dependencies
        health_status['actions_loaded'] = len(self.actions_config.get("actions", {}))
        health_status['actions_file'] = self.actions_file
        return health_status 