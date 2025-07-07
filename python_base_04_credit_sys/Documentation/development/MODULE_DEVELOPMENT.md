# Module Development Guide

## 🎯 Overview

This guide walks you through creating new modules for the Flask Credit System. Modules are the primary way to extend functionality and organize business logic.

## 📋 Prerequisites

- Understanding of the [Module-First Architecture](../architecture/MODULE_FIRST_ARCHITECTURE.md)
- Familiarity with the [Module System](../modules/MODULE_SYSTEM.md)
- Python 3.11+ development environment
- Access to the codebase

## 🚀 Quick Start: Creating Your First Module

### **Step 1: Create Module File**
Create a new file in `core/modules/`:

```bash
touch core/modules/my_new_module.py
```

### **Step 2: Implement BaseModule Interface**
```python
# core/modules/my_new_module.py
from core.modules.base_module import BaseModule
from tools.logger.custom_logger import custom_log
from datetime import datetime
from flask import request, jsonify

class MyNewModule(BaseModule):
    NAME = "my_new_module"
    DEPENDENCIES = ['connection_api']  # Declare any dependencies
    
    def __init__(self):
        super().__init__()
        self.connection_api = None
        self.db = None
        self.initialized_at = None
    
    def initialize(self, app_manager) -> bool:
        """Initialize the module with dependencies"""
        try:
            custom_log(f"Initializing {self.NAME}...")
            
            # Access dependencies
            self.connection_api = app_manager.module_manager.get_module('connection_api')
            if not self.connection_api:
                custom_log(f"❌ {self.NAME}: Required dependency 'connection_api' not available")
                return False
            
            # Access infrastructure managers
            self.db = app_manager.database_manager
            self.redis = app_manager.redis_manager
            
            # Module-specific initialization
            self.initialized_at = datetime.utcnow()
            
            custom_log(f"✅ {self.NAME} initialized successfully")
            return True
            
        except Exception as e:
            custom_log(f"❌ Failed to initialize {self.NAME}: {e}")
            return False
    
    def register_routes(self, app):
        """Register Flask routes for this module"""
        
        @app.route('/my-module/info', methods=['GET'])
        def get_module_info():
            """Get module information"""
            return jsonify({
                "module": self.NAME,
                "status": "active",
                "initialized_at": self.initialized_at.isoformat() if self.initialized_at else None,
                "dependencies": self.DEPENDENCIES
            })
        
        @app.route('/my-module/data', methods=['GET', 'POST'])
        def handle_data():
            """Handle data operations"""
            if request.method == 'GET':
                return self._get_data()
            elif request.method == 'POST':
                return self._create_data(request.json)
    
    def health_check(self) -> dict:
        """Return module health status"""
        try:
            # Check database connection
            db_healthy = self.db.is_connected() if self.db else False
            
            # Check dependencies
            dependencies_healthy = self.connection_api is not None
            
            # Overall health
            healthy = db_healthy and dependencies_healthy
            
            return {
                "status": "healthy" if healthy else "unhealthy",
                "module": self.NAME,
                "database_connection": db_healthy,
                "dependencies_available": dependencies_healthy,
                "uptime_seconds": (datetime.utcnow() - self.initialized_at).total_seconds() if self.initialized_at else 0,
                "last_check": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "module": self.NAME,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    # Private methods for module logic
    def _get_data(self):
        """Get data from database"""
        try:
            # Use connection API or direct database access
            collection = self.db.get_collection('my_module_data')
            data = list(collection.find({}))
            
            return jsonify({
                "success": True,
                "data": data,
                "count": len(data)
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    def _create_data(self, data):
        """Create new data record"""
        try:
            # Validate input
            if not data or 'name' not in data:
                return jsonify({
                    "success": False,
                    "error": "Missing required field: name"
                }), 400
            
            # Insert into database
            collection = self.db.get_collection('my_module_data')
            result = collection.insert_one({
                **data,
                "created_at": datetime.utcnow(),
                "module": self.NAME
            })
            
            return jsonify({
                "success": True,
                "id": str(result.inserted_id),
                "message": "Data created successfully"
            })
            
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
```

### **Step 3: Test Your Module**
```bash
# Test module discovery and initialization
python3 -c "
from core.managers.module_registry import ModuleRegistry
modules = ModuleRegistry.get_modules()
print('Discovered modules:', list(modules.keys()))
"
```

### **Step 4: Run the Application**
```bash
python3 app.py
```

Your module will be automatically discovered, initialized, and its routes will be available!

## 🔧 Advanced Module Development

### **Complex Dependencies**
For modules with multiple dependencies:

```python
class AdvancedModule(BaseModule):
    NAME = "advanced_module"
    DEPENDENCIES = ['connection_api', 'user_management', 'wallet_module']
    
    def initialize(self, app_manager) -> bool:
        # Access all dependencies
        self.connection_api = app_manager.module_manager.get_module('connection_api')
        self.user_management = app_manager.module_manager.get_module('user_management')
        self.wallet_module = app_manager.module_manager.get_module('wallet_module')
        
        # Validate all dependencies are available
        missing_deps = []
        for dep in self.DEPENDENCIES:
            if not app_manager.module_manager.get_module(dep):
                missing_deps.append(dep)
        
        if missing_deps:
            custom_log(f"❌ {self.NAME}: Missing dependencies: {missing_deps}")
            return False
        
        return True
```

### **Database Operations**
Use consistent database patterns:

```python
def _get_user_records(self, user_id: str):
    """Get records for a specific user"""
    try:
        # Get collection
        collection = self.db.get_collection('user_records')
        
        # Query with proper error handling
        records = list(collection.find({
            "user_id": user_id,
            "active": True
        }).sort("created_at", -1))
        
        return records
        
    except Exception as e:
        custom_log(f"Database error in {self.NAME}: {e}")
        raise

def _create_user_record(self, user_id: str, data: dict):
    """Create a new user record"""
    try:
        collection = self.db.get_collection('user_records')
        
        record = {
            "user_id": user_id,
            "data": data,
            "created_at": datetime.utcnow(),
            "active": True,
            "module": self.NAME
        }
        
        result = collection.insert_one(record)
        return str(result.inserted_id)
        
    except Exception as e:
        custom_log(f"Database error in {self.NAME}: {e}")
        raise
```

### **Caching Integration**
Integrate with Redis for performance:

```python
def _get_cached_data(self, key: str):
    """Get data from cache with fallback to database"""
    try:
        # Try cache first
        if self.redis:
            cached = self.redis.get(f"{self.NAME}:{key}")
            if cached:
                return json.loads(cached)
        
        # Fallback to database
        data = self._get_data_from_db(key)
        
        # Cache the result
        if self.redis and data:
            self.redis.setex(
                f"{self.NAME}:{key}",
                300,  # 5 minutes TTL
                json.dumps(data)
            )
        
        return data
        
    except Exception as e:
        custom_log(f"Cache error in {self.NAME}: {e}")
        # Return database data even if caching fails
        return self._get_data_from_db(key)
```

### **Authentication & Authorization**
Integrate with JWT authentication:

```python
from functools import wraps
from flask import request, jsonify

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get JWT token from header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid authorization header"}), 401
        
        token = auth_header.split(' ')[1]
        
        # Validate token using JWT manager
        try:
            jwt_manager = app_manager.jwt_manager
            payload = jwt_manager.decode_token(token)
            request.user_id = payload.get('user_id')
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": "Invalid token"}), 401
    
    return decorated_function

# Use in routes
@app.route('/my-module/protected', methods=['GET'])
@require_auth
def protected_endpoint():
    user_id = request.user_id
    return jsonify({"message": f"Hello user {user_id}"})
```

## 🧪 Testing Your Module

### **Unit Tests**
Create tests for your module:

```python
# tests/test_my_new_module.py
import unittest
from unittest.mock import Mock, patch
from core.modules.my_new_module import MyNewModule

class TestMyNewModule(unittest.TestCase):
    
    def setUp(self):
        self.module = MyNewModule()
        self.mock_app_manager = Mock()
        
    def test_module_initialization(self):
        """Test module initializes correctly"""
        # Mock dependencies
        mock_connection_api = Mock()
        self.mock_app_manager.module_manager.get_module.return_value = mock_connection_api
        
        # Test initialization
        result = self.module.initialize(self.mock_app_manager)
        
        self.assertTrue(result)
        self.assertEqual(self.module.connection_api, mock_connection_api)
    
    def test_health_check(self):
        """Test health check returns correct status"""
        # Setup module state
        self.module.connection_api = Mock()
        self.module.db = Mock()
        self.module.db.is_connected.return_value = True
        
        # Run health check
        health = self.module.health_check()
        
        self.assertEqual(health['status'], 'healthy')
        self.assertEqual(health['module'], 'my_new_module')

if __name__ == '__main__':
    unittest.main()
```

### **Integration Tests**
Test module integration with the full system:

```python
# tests/integration/test_module_integration.py
import requests
import unittest

class TestModuleIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Start the application for testing"""
        # Start Flask app in test mode
        pass
    
    def test_module_endpoints(self):
        """Test module endpoints are accessible"""
        response = requests.get('http://localhost:5000/my-module/info')
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['module'], 'my_new_module')
    
    def test_module_health(self):
        """Test module health endpoint"""
        response = requests.get('http://localhost:5000/modules/my_new_module/health')
        self.assertEqual(response.status_code, 200)
        
        health = response.json()
        self.assertIn('status', health)
```

## 📚 Module Documentation

Document your module comprehensively:

```markdown
# My New Module

## Purpose
Brief description of what this module does.

## Dependencies
- connection_api: Required for database operations

## Endpoints
- `GET /my-module/info` - Get module information
- `GET /my-module/data` - Retrieve data
- `POST /my-module/data` - Create new data

## Configuration
Any configuration requirements or environment variables.

## Examples
Code examples showing how to use the module.
```

## 🚀 Deployment Considerations

### **Environment Configuration**
Add module-specific configuration:

```python
# In module initialization
def initialize(self, app_manager) -> bool:
    # Get module-specific config
    self.config = {
        'cache_ttl': int(os.getenv('MY_MODULE_CACHE_TTL', 300)),
        'batch_size': int(os.getenv('MY_MODULE_BATCH_SIZE', 100)),
        'enabled_features': os.getenv('MY_MODULE_FEATURES', '').split(',')
    }
```

### **Resource Requirements**
Document any additional resources your module needs:
- Database collections
- Redis keyspaces  
- External service access
- File system permissions

### **Monitoring**
Add module-specific metrics:

```python
from core.metrics import module_metrics

def _process_request(self):
    with module_metrics.timer(f'{self.NAME}_request_duration'):
        # Process request
        result = self._do_work()
        
    module_metrics.increment(f'{self.NAME}_requests_total')
    return result
```

## ✅ Module Development Checklist

Before deploying your module, ensure:

- [ ] Implements BaseModule interface correctly
- [ ] Declares all dependencies explicitly
- [ ] Handles initialization failures gracefully
- [ ] Implements comprehensive health checks
- [ ] Includes proper error handling
- [ ] Has unit tests covering core functionality
- [ ] Documents all endpoints and usage
- [ ] Follows naming conventions
- [ ] Logs important operations
- [ ] Handles database/cache failures
- [ ] Validates input data
- [ ] Returns consistent response formats

---

*Following this guide ensures your modules integrate seamlessly with the Flask Credit System while maintaining high quality and reliability standards.* 