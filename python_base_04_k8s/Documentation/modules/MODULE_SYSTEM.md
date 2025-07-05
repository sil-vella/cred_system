# Module System Overview

## 🧩 Introduction

The Module System is the heart of our Flask Credit System, providing a structured way to organize business logic into independent, reusable components. Each module represents a specific domain of functionality and can interact with other modules through well-defined interfaces.

## 📋 Current Active Modules

| Module | Purpose | Dependencies | Status |
|--------|---------|--------------|---------|
| `connection_api` | Core database operations & API base | None | ✅ Active |
| `user_management` | User authentication & CRUD | `connection_api` | ✅ Active |
| `wallet_module` | Credit balance management | `connection_api`, `user_management` | ✅ Active |
| `transactions_module` | Transaction processing | `connection_api`, `user_management`, `wallet_module` | ✅ Active |

## 🏗️ Module Architecture

### **BaseModule Interface**
Every module must inherit from `BaseModule` and implement three core methods:

```python
from abc import ABC, abstractmethod

class BaseModule(ABC):
    NAME = None  # Module identifier
    DEPENDENCIES = []  # List of required module dependencies
    
    @abstractmethod
    def initialize(self, app_manager) -> bool:
        """
        Initialize module with dependencies and resources.
        Should set self.app = app_manager.flask_app for route registration.
        Should call self.register_routes() after setting self.app.
        """
        pass
    
    @abstractmethod  
    def register_routes(self, app):
        """Register Flask routes for this module"""
        pass
    
    @abstractmethod
    def health_check(self) -> dict:
        """Return current health status of the module"""
        pass
```

## 🔄 Module Lifecycle

### **1. Discovery**
```python
# ModuleRegistry automatically scans core/modules/ directory
modules = ModuleRegistry.get_modules()
# Returns: {'connection_api': ConnectionAPIModule, 'user_management': UserManagementModule, ...}
```

### **2. Dependency Resolution**
```python
# Analyze dependencies and create load order
load_order = ModuleRegistry.get_module_load_order()
# Returns: ['connection_api', 'user_management', 'wallet_module', 'transactions_module']

# Detect circular dependencies
circular_deps = ModuleRegistry.has_circular_dependencies()
# Returns: False (no circular dependencies)
```

### **3. Initialization**
```python
for module_name in load_order:
    module_class = modules[module_name]
    module_instance = module_class()
    
    # Initialize with app_manager providing access to all infrastructure
    success = module_instance.initialize(app_manager)
    
    if success:
        # Store initialized module
        module_manager.modules[module_name] = module_instance
        custom_log(f"✅ Module '{module_name}' initialized successfully")
    else:
        custom_log(f"❌ Module '{module_name}' initialization failed")
```
> **Note:** Each module is responsible for calling `self.register_routes()` inside its own `initialize` method after setting `self.app = app_manager.flask_app`.

### **4. Runtime Operations**
```python
# Access other modules
user_module = app_manager.module_manager.get_module('user_management')

# Check module health
health = app_manager.module_manager.get_module_health('wallet_module')

# Get system-wide module status
status = app_manager.module_manager.get_module_status()
```

## 🔗 Inter-Module Communication

### **Dependency Injection Pattern**
Modules access their dependencies through the app_manager:

```python
class WalletModule(BaseModule):
    NAME = "wallet_module"
    DEPENDENCIES = ['connection_api', 'user_management']
    
    def initialize(self, app_manager) -> bool:
        # Access dependencies
        self.connection_api = app_manager.module_manager.get_module('connection_api')
        self.user_management = app_manager.module_manager.get_module('user_management')
        
        # Access infrastructure managers
        self.db = app_manager.database_manager
        self.redis = app_manager.redis_manager
        
        # Set Flask app for route registration
        self.app = app_manager.flask_app
        self.register_routes()
        return True
```

### **Safe Module Access**
```python
def get_user_balance(self, user_id: str):
    # Safe access to user_management module
    user_module = self.user_management
    if not user_module:
        raise ModuleDependencyError("User management module not available")
    
    # Verify user exists before processing
    user = user_module.get_user_by_id(user_id)
    if not user:
        raise UserNotFoundError(f"User {user_id} not found")
    
    # Process wallet operation
    return self._get_balance_from_db(user_id)
```

## 📊 Module Health Monitoring

### **Health Check Interface**
Each module implements health checking:

```python
def health_check(self) -> dict:
    """Return comprehensive health status"""
    try:
        # Check module-specific resources
        db_healthy = self._check_database_connection()
        dependencies_healthy = self._check_dependencies()
        
        return {
            "status": "healthy" if (db_healthy and dependencies_healthy) else "unhealthy",
            "module": self.NAME,
            "database_connection": db_healthy,
            "dependencies": {
                dep: self._check_dependency_health(dep) 
                for dep in self.DEPENDENCIES
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
```

### **System Health Endpoints**
- `GET /modules/status` - Overall module system status
- `GET /modules/{module_name}/health` - Individual module health
- `GET /health` - Application-wide health check including modules

## 🛠️ Module Development Best Practices

### **1. Single Responsibility**
Each module should have one clear purpose:
```python
# ✅ Good - Clear responsibility
class WalletModule(BaseModule):
    """Handles credit balance operations only"""
    
# ❌ Bad - Multiple responsibilities  
class WalletAndNotificationModule(BaseModule):
    """Handles wallet AND notifications"""
```

### **2. Explicit Dependencies**
Always declare dependencies explicitly:
```python
class TransactionModule(BaseModule):
    NAME = "transactions_module"
    DEPENDENCIES = ['connection_api', 'user_management', 'wallet_module']  # ✅ Clear dependencies
```

### **3. Graceful Failure Handling**
```python
def initialize(self, app_manager) -> bool:
    try:
        # Critical initialization
        self.db = app_manager.database_manager
        if not self.db.is_connected():
            custom_log(f"Database not available for {self.NAME}")
            return False
            
        # Optional initialization
        try:
            self.cache = app_manager.redis_manager
        except Exception as e:
            custom_log(f"Cache unavailable for {self.NAME}, continuing without cache: {e}")
            self.cache = None
            
        # Set Flask app and register routes
        self.app = app_manager.flask_app
        self.register_routes()
        return True
    except Exception as e:
        custom_log(f"Critical error initializing {self.NAME}: {e}")
        return False
```

### **4. Route Organization**
Organize routes by module domain:
```python
def register_routes(self, app):
    @app.route('/wallet/balance/<user_id>', methods=['GET'])
    def get_balance(user_id):
        return self.get_user_balance(user_id)
    
    @app.route('/wallet/deposit', methods=['POST'])
    def deposit():
        return self.process_deposit(request.json)
    
    @app.route('/wallet/withdraw', methods=['POST'])  
    def withdraw():
        return self.process_withdrawal(request.json)
```

## 🔍 Module Debugging

### **Module Status Inspection**
```python
# Check if module is loaded
module_manager = app_manager.module_manager
is_loaded = module_manager.is_module_loaded('wallet_module')

# Get module instance
wallet_module = module_manager.get_module('wallet_module')

# Check module health
health = module_manager.get_module_health('wallet_module')
```

### **Dependency Debugging**
```python
# Check dependency graph
dependencies = ModuleRegistry.get_dependency_graph()
print(f"Dependency graph: {dependencies}")

# Check load order
load_order = ModuleRegistry.get_module_load_order()  
print(f"Load order: {load_order}")

# Check for circular dependencies
if ModuleRegistry.has_circular_dependencies():
    print("⚠️ Circular dependencies detected!")
```

## 📈 Performance Considerations

### **Module Initialization Time**
- Keep initialization fast (< 1 second per module)
- Defer expensive operations to first use
- Use lazy loading for optional dependencies

### **Memory Usage**
- Each module maintains its own state
- Share expensive resources through managers
- Clean up resources in module disposal

### **Route Performance**
- Use module-level caching where appropriate
- Implement efficient database queries
- Monitor per-module response times

## 🚀 Future Module Development

### **Planned Modules**
- `notification_module`: Email/SMS notifications
- `reporting_module`: Analytics and reporting
- `audit_module`: Audit trail and compliance
- `integration_module`: Third-party service integrations

### **Module Guidelines**
1. Follow the BaseModule interface strictly
2. Implement comprehensive health checks
3. Document all dependencies clearly
4. Provide extensive logging for debugging
5. Include unit tests for all module functionality

---

*The Module System enables scalable, maintainable code organization. Each module can be developed, tested, and deployed independently while maintaining clear boundaries and dependencies.* 