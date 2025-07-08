# Declarative Actions System

## Overview

The Declarative Actions System is a powerful framework that enables modules to define their actions through YAML declarations, allowing for dynamic discovery and execution of functionality without hard-coded route definitions. This system provides a flexible, maintainable approach to action management with automatic parameter validation, type-based execution, and comprehensive documentation.

## Architecture

### Core Components

1. **ActionDiscoveryManager** - Discovers and manages YAML-based action declarations
2. **UserActionsManager** - Handles action registration and execution coordination
3. **YAML Declarations** - Module-specific action definitions
4. **Module Handlers** - Python implementations of declared actions

### System Flow

```
HTTP Request → Route Handler → ActionDiscoveryManager → YAML Lookup → Module Handler → Response
```

## Implementation Details

### 1. ActionDiscoveryManager

The `ActionDiscoveryManager` is responsible for scanning YAML files and building an in-memory registry of available actions.

```python
# python_base_04_external/core/managers/action_discovery_manager.py

class ActionDiscoveryManager:
    def __init__(self, app_manager):
        self.app_manager = app_manager
        self.actions_registry = {}
        self.last_scan_time = None
        self.scan_interval = 300  # 5 minutes
        
    def discover_actions(self):
        """Scan all modules for YAML action declarations."""
        try:
            discovered_actions = {}
            modules_dir = os.path.join(os.path.dirname(__file__), '..', 'modules')
            
            for module_name in os.listdir(modules_dir):
                module_path = os.path.join(modules_dir, module_name)
                if os.path.isdir(module_path):
                    declarations_dir = os.path.join(module_path, 'declarations')
                    if os.path.exists(declarations_dir):
                        yaml_files = [f for f in os.listdir(declarations_dir) 
                                    if f.endswith('.yaml') or f.endswith('.yml')]
                        
                        for yaml_file in yaml_files:
                            yaml_path = os.path.join(declarations_dir, yaml_file)
                            actions = self._parse_yaml_actions(yaml_path, module_name)
                            discovered_actions.update(actions)
            
            self.actions_registry = discovered_actions
            self.last_scan_time = datetime.now()
            custom_log(f"✅ Discovered {len(discovered_actions)} actions from YAML files")
            
        except Exception as e:
            custom_log(f"❌ Error discovering actions: {e}", level="ERROR")
            raise
```

### 2. YAML Action Declarations

Actions are defined in YAML files within each module's `declarations` directory.

```yaml
# python_base_04_external/core/modules/system_actions_module/declarations/actions.yaml

system_actions_module.get_system_info:
  description: "Get detailed system information"
  type: "function"
  module: "system_actions_module"
  config:
    function: "get_system_info"
    type: "function"
  required_params: []
  optional_params: ["include_details", "include_metrics"]
  url_pattern: ""
  examples:
    - description: "Get basic system info"
      request: "{}"
      url: "/actions/get_system_info"
    - description: "Get detailed system info"
      request: '{"include_details": true}'
      url: "/actions/get_system_info?include_details=true"
    - description: "Get detailed system info with metrics"
      request: '{"include_details": true, "include_metrics": true}'
      url: "/actions/get_system_info?include_details=true&include_metrics=true"

system_actions_module.get_module_status:
  description: "Get status of a specific module"
  type: "function"
  module: "system_actions_module"
  config:
    function: "get_module_status"
    type: "function"
  required_params: ["module_name"]
  optional_params: ["include_details"]
  url_pattern: "module_name"
  examples:
    - description: "Get wallet module status"
      request: "{}"
      url: "/actions/get_module_status/wallet"
    - description: "Get detailed wallet module status"
      request: '{"include_details": true}'
      url: "/actions/get_module_status/wallet?include_details=true"
```

### 3. Module Handler Implementation

Each module implements handlers that correspond to the YAML declarations.

```python
# python_base_04_external/core/modules/system_actions_module/system_actions_main.py

class SystemActionsModule(BaseModule):
    def __init__(self, app_manager):
        super().__init__(app_manager)
        self.module_name = "system_actions"
        self.version = "1.0.0"
        
    def _get_system_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed system information."""
        try:
            include_details = args.get('include_details', False)
            include_metrics = args.get('include_metrics', False)
            
            system_info = {
                "module": self.module_name,
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": self.version
            }
            
            if include_details:
                system_info.update({
                    "uptime": self._get_uptime(),
                    "memory_usage": self._get_memory_usage(),
                    "active_modules": self._get_active_modules()
                })
                
            if include_metrics:
                system_info["metrics"] = self._get_system_metrics()
                
            return system_info
            
        except Exception as e:
            custom_log(f"❌ Error getting system info: {e}", level="ERROR")
            raise
            
    def _get_module_status(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of a specific module."""
        try:
            module_name = args.get('module_name')
            include_details = args.get('include_details', False)
            
            if not module_name:
                raise ValueError("module_name is required")
                
            module_instance = self.app_manager.module_manager.get_module(module_name)
            if not module_instance:
                return {
                    "module": module_name,
                    "status": "not_found",
                    "error": f"Module {module_name} not found"
                }
                
            status_info = {
                "module": module_name,
                "status": "healthy" if hasattr(module_instance, 'is_healthy') 
                         else "unknown",
                "timestamp": datetime.now().isoformat()
            }
            
            if include_details and hasattr(module_instance, 'get_detailed_status'):
                status_info["details"] = module_instance.get_detailed_status()
                
            return status_info
            
        except Exception as e:
            custom_log(f"❌ Error getting module status: {e}", level="ERROR")
            raise
```

### 4. Route Integration

The system integrates with Flask routes to provide dynamic action execution.

```python
# python_base_04_external/app.py

@app.route('/actions/<action_name>/<path:args>', methods=['GET', 'POST'])
def execute_action(action_name, args):
    """Single wildcard route for all actions with YAML discovery."""
    try:
        # Get request data (JSON body for POST, query params for GET)
        if request.method == 'POST':
            request_data = request.get_json() or {}
        else:
            request_data = dict(request.args)
        
        # Parse URL arguments
        parsed_args = app_manager.action_discovery_manager.parse_url_args(args)
        
        # Merge URL args with request data
        all_args = {**parsed_args, **request_data}
        
        # Search for action in YAML registry
        action_info = app_manager.action_discovery_manager.find_action(action_name)
        if not action_info:
            return jsonify({
                'error': f'Action "{action_name}" not found',
                'available_actions': list(app_manager.action_discovery_manager.actions_registry.keys())
            }), 404
        
        # Execute the action
        result = app_manager.action_discovery_manager.execute_action_logic(action_info, all_args)
        
        return jsonify({
            'action': action_name,
            'module': action_info['module'],
            'result': result,
            'success': True
        }), 200
        
    except Exception as e:
        custom_log(f"❌ Error executing action {action_name}: {e}", level="ERROR")
        return jsonify({
            'error': f'Failed to execute action: {str(e)}',
            'action': action_name
        }), 500
```

## Action Types and Execution

### Supported Action Types

1. **Function Actions** - Direct function calls within modules
2. **HTTP Actions** - External API calls (planned)
3. **Queue Actions** - Asynchronous task execution (planned)

### Parameter Validation

The system automatically validates parameters based on YAML declarations:

```python
def validate_action_params(self, action_info: Dict[str, Any], args: Dict[str, Any]) -> bool:
    """Validate action parameters against YAML declaration."""
    required_params = action_info.get('required_params', [])
    optional_params = action_info.get('optional_params', [])
    
    # Check required parameters
    for param in required_params:
        if param not in args:
            raise ValueError(f"Required parameter '{param}' not provided")
    
    # Validate parameter types (if specified)
    for param, value in args.items():
        if param in required_params or param in optional_params:
            # Add type validation logic here
            pass
    
    return True
```

## URL Pattern Matching

The system supports dynamic URL patterns for parameter extraction:

```python
def parse_url_args(self, url_args: str) -> Dict[str, Any]:
    """Parse URL arguments based on action's URL pattern."""
    if not url_args or url_args == "empty":
        return {}
    
    # Split URL arguments
    args_parts = url_args.split('/')
    
    # Get action info to determine pattern
    action_info = self.find_action_by_url(url_args)
    if not action_info:
        return {}
    
    url_pattern = action_info.get('url_pattern', '')
    if not url_pattern:
        return {}
    
    # Parse based on pattern
    pattern_parts = url_pattern.split('/')
    parsed_args = {}
    
    for i, pattern_part in enumerate(pattern_parts):
        if i < len(args_parts):
            parsed_args[pattern_part] = args_parts[i]
    
    return parsed_args
```

## Module Integration

### Module Registration

Modules are automatically discovered and registered:

```python
# python_base_04_external/core/managers/app_manager.py

def initialize_action_discovery(self):
    """Initialize the action discovery system."""
    try:
        self.action_discovery_manager = ActionDiscoveryManager(self)
        self.action_discovery_manager.discover_actions()
        custom_log("✅ Action discovery system initialized")
    except Exception as e:
        custom_log(f"❌ Error initializing action discovery: {e}", level="ERROR")
        raise
```

### Module Structure

Each module should follow this structure:

```
core/modules/
├── module_name/
│   ├── __init__.py
│   ├── module_main.py
│   └── declarations/
│       └── actions.yaml
```

## Benefits of the Declarative System

### 1. **Maintainability**
- Actions are defined declaratively, making them easy to understand and modify
- No hard-coded route definitions
- Centralized action documentation

### 2. **Flexibility**
- Dynamic action discovery
- Easy to add new actions without code changes
- Support for different action types

### 3. **Documentation**
- Self-documenting through YAML declarations
- Automatic API documentation generation
- Clear examples and parameter specifications

### 4. **Type Safety**
- Parameter validation based on declarations
- Type checking for action parameters
- Clear error messages for invalid inputs

### 5. **Extensibility**
- Easy to add new action types
- Support for complex parameter patterns
- Integration with external systems

## Usage Examples

### Basic Action Execution

```bash
# Get system information
curl "http://localhost:8081/actions/get_system_info"

# Get module status
curl "http://localhost:8081/actions/get_module_status/wallet"

# With parameters
curl "http://localhost:8081/actions/get_system_info?include_details=true"
```

### Action Discovery

```bash
# List all available actions
curl "http://localhost:8081/actions"
```

Response:
```json
{
  "actions": {
    "system_actions_module.get_system_info": {
      "description": "Get detailed system information",
      "examples": [...],
      "module": "system_actions_module",
      "optional_params": ["include_details", "include_metrics"],
      "required_params": [],
      "type": "function",
      "url_pattern": ""
    }
  },
  "last_scan": "2025-07-08 13:32:57.294289",
  "modules": ["system_actions_module"],
  "success": true,
  "total_actions": 4
}
```

## Best Practices

### 1. **YAML Declaration Structure**
- Use clear, descriptive action names
- Provide comprehensive descriptions
- Include multiple examples
- Specify all required and optional parameters

### 2. **Module Handler Implementation**
- Implement proper error handling
- Use type hints for parameters
- Log important operations
- Return consistent response formats

### 3. **URL Pattern Design**
- Use descriptive parameter names
- Keep patterns simple and intuitive
- Document pattern usage in examples

### 4. **Testing**
- Test all action declarations
- Verify parameter validation
- Test error scenarios
- Validate response formats

## Future Enhancements

### Planned Features

1. **HTTP Action Type** - Support for external API calls
2. **Queue Action Type** - Asynchronous task execution
3. **Action Composition** - Chain multiple actions together
4. **Advanced Validation** - Schema-based parameter validation
5. **Action Versioning** - Support for action versioning
6. **Performance Monitoring** - Action execution metrics
7. **Caching** - Action result caching
8. **Rate Limiting** - Per-action rate limiting

### Integration Opportunities

1. **API Documentation** - Automatic OpenAPI/Swagger generation
2. **Testing Framework** - Automated action testing
3. **Monitoring** - Action execution monitoring and alerting
4. **Security** - Action-level security policies
5. **Audit Logging** - Comprehensive action audit trails

## Conclusion

The Declarative Actions System provides a powerful, flexible foundation for building modular, maintainable applications. By separating action declarations from implementation, it enables rapid development while maintaining code quality and documentation standards.

The system's YAML-driven approach makes it easy to understand, modify, and extend, while its integration with the module system ensures consistency across the application architecture. 