# Getting Started

## 🚀 Welcome to Flask Credit System

This guide will help you set up the development environment and understand the Flask Credit System's module-first architecture.

## 📋 Prerequisites

### **Required Software**
- **Python 3.11+** - Runtime environment
- **MongoDB** - Primary database (local or remote)
- **Redis** - Caching and session storage (local or remote)
- **HashiCorp Vault** - Secrets management (optional for local dev)
- **Git** - Version control

### **Optional Tools**
- **Docker** - Container development
- **Kubernetes** - Production deployment
- **VS Code** - Recommended IDE with Python extensions

## 🔧 Environment Setup

### **Step 1: Clone Repository**
```bash
git clone <repository-url>
cd app_dev_new_playbooks/python_base_04_k8s
```

### **Step 2: Python Environment**
The project includes a complete Python environment in the `libs/` directory:

```bash
# Verify Python version
python3 --version  # Should be 3.11+

# The project uses a custom libs directory instead of venv
# All dependencies are pre-installed in libs/
export PYTHONPATH="${PWD}/libs:${PYTHONPATH}"
```

### **Step 3: Environment Variables**
Create a `.env` file or set environment variables:

```bash
# Core Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# Database Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=credit_system
MONGODB_TIMEOUT=30

# Redis Configuration  
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# Vault Configuration (Optional for local dev)
VAULT_URL=http://localhost:8200
VAULT_ROLE_ID=your-role-id
VAULT_SECRET_ID=your-secret-id

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret
JWT_ACCESS_TOKEN_EXPIRES=3600

# Application Configuration
APP_NAME=Flask Credit System
APP_VERSION=1.0.0
LOG_LEVEL=INFO
```

### **Step 4: Infrastructure Setup**

#### **Option A: Local Services**
```bash
# MongoDB (using Docker)
docker run -d --name mongodb -p 27017:27017 mongo:latest

# Redis (using Docker)  
docker run -d --name redis -p 6379:6379 redis:latest

# Or install locally using your package manager
```

#### **Option B: Kubernetes (Development)**
```bash
# If you have access to the k8s environment
kubectl apply -f k8s/mongodb/
kubectl apply -f k8s/redis/
kubectl port-forward svc/mongodb 27017:27017
kubectl port-forward svc/redis 6379:6379
```

## 🏃 Running the Application

### **Quick Start**
```bash
# From python_base_04_k8s directory
python3 app.py
```

Expected output:
```
🔧 Initializing Flask Credit System...
⚠️ VaultManager initialization failed: VAULT_ROLE_ID environment variable not set
✅ Database manager initialized
✅ Redis manager initialized  
✅ JWT manager initialized
🔍 Discovering modules...
✅ Found 4 modules: ['connection_api', 'user_management', 'wallet', 'transactions']
📊 Module load order: ['connection_api', 'user_management', 'wallet', 'transactions']
✅ Module 'wallet' initialized successfully
✅ Module 'transactions' initialized successfully
🌟 Flask app is running on http://localhost:5000
```

### **Verify Installation**
Test the application endpoints:

```bash
# Health check
curl http://localhost:5000/health

# Module status
curl http://localhost:5000/modules/status

# Individual module health
curl http://localhost:5000/modules/wallet/health
```

## 🧩 Understanding the Architecture

### **Module-First Architecture**
The system is organized around modules, not plugins:

```
core/
├── modules/                    # 🎯 Business logic modules
│   ├── base_module.py         # Abstract base class
│   ├── connection_api.py      # Database operations
│   ├── user_management.py     # User auth & CRUD
│   ├── wallet_module.py       # Credit balance management  
│   └── transactions_module.py # Transaction processing
├── managers/                   # 🏗️ Infrastructure managers
│   ├── app_manager.py         # Application orchestrator
│   ├── module_manager.py      # Module lifecycle
│   ├── database_manager.py    # MongoDB operations
│   ├── redis_manager.py       # Redis operations
│   └── ...
```

### **Application Flow**
```
HTTP Request → Flask App → AppManager → ModuleManager → Specific Module → Response
```

### **Module Dependencies**
```
connection_api (no dependencies)
├── user_management (depends on: connection_api)
    ├── wallet_module (depends on: connection_api, user_management)
        └── transactions_module (depends on: connection_api, user_management, wallet_module)
```

## 🔍 Exploring the System

### **Available Endpoints**
```bash
# System Health
GET  /health                          # Application health
GET  /modules/status                  # All modules status
GET  /modules/{module_name}/health    # Specific module health

# Module Endpoints (examples)
GET  /wallet/info                     # Wallet module info  
GET  /transactions/info               # Transactions module info

# Note: Full API documentation in Documentation/api/
```

### **Module Introspection**
```python
# In Python console or script
from core.managers.module_registry import ModuleRegistry
from core.managers.module_manager import ModuleManager

# Discover modules
modules = ModuleRegistry.get_modules()
print("Available modules:", list(modules.keys()))

# Check dependencies
load_order = ModuleRegistry.get_module_load_order()
print("Load order:", load_order)
```

## 🛠️ Development Workflow

### **1. Understanding Modules**
Start by exploring existing modules:

```bash
# Read module code
cat core/modules/wallet_module.py

# Check module health
curl http://localhost:5000/modules/wallet/health
```

### **2. Creating Your First Module**
Follow the [Module Development Guide](MODULE_DEVELOPMENT.md):

```python
# Create core/modules/my_module.py
from core.modules.base_module import BaseModule

class MyModule(BaseModule):
    NAME = "my_module"
    DEPENDENCIES = ['connection_api']
    
    def initialize(self, app_manager) -> bool:
        # Your initialization code
        return True
    
    def register_routes(self, app):
        # Your Flask routes
        pass
    
    def health_check(self) -> dict:
        # Your health check logic
        return {"status": "healthy", "module": self.NAME}
```

### **3. Testing Your Changes**
```bash
# Restart the application to pick up new modules
python3 app.py

# Test your module
curl http://localhost:5000/modules/my_module/health
```

## 🔧 Development Tools

### **Logging**
The system uses custom logging:

```python
from tools.logger.custom_logger import custom_log

custom_log("Your debug message")
custom_log("Error occurred", level="ERROR")
```

### **Database Operations**
Access database through managers:

```python
def your_function(self, app_manager):
    # Access database
    db = app_manager.database_manager
    collection = db.get_collection('your_collection')
    
    # Perform operations
    result = collection.find_one({"field": "value"})
    return result
```

### **Configuration Access**
Access configuration through managers:

```python
def your_function(self, app_manager):
    # Access configuration
    config = app_manager.config_manager
    value = config.get('YOUR_SETTING', 'default_value')
    return value
```

## 🚨 Common Issues & Solutions

### **Issue: Module Not Found**
```
❌ Module 'my_module' not found
```
**Solution**: Ensure your module file is in `core/modules/` and implements BaseModule

### **Issue: Database Connection Failed**
```
❌ Failed to connect to MongoDB
```
**Solution**: 
- Check MongoDB is running: `docker ps` or `brew services list`
- Verify connection string in environment variables
- Check network connectivity

### **Issue: Import Errors**
```
❌ ModuleNotFoundError: No module named 'core'
```
**Solution**: Set PYTHONPATH correctly:
```bash
export PYTHONPATH="${PWD}/libs:${PWD}:${PYTHONPATH}"
```

### **Issue: Circular Dependencies**
```
❌ Circular dependency detected
```
**Solution**: Review module dependencies and remove circular references

## 📚 Next Steps

### **For New Developers**
1. Read [System Overview](../architecture/SYSTEM_OVERVIEW.md)
2. Understand [Module-First Architecture](../architecture/MODULE_FIRST_ARCHITECTURE.md)
3. Explore [Module System](../modules/MODULE_SYSTEM.md)
4. Try [Module Development](MODULE_DEVELOPMENT.md)

### **For Experienced Developers**
1. Review [API Documentation](../api/API_OVERVIEW.md)
2. Check [Deployment Guide](../deployment/DEPLOYMENT_OVERVIEW.md)
3. Understand [Migration History](../migration/PLUGIN_TO_MODULE_MIGRATION.md)

### **For DevOps Engineers**
1. Review [Kubernetes Guide](../deployment/KUBERNETES_GUIDE.md)
2. Check [Docker Guide](../deployment/DOCKER_GUIDE.md)
3. Setup [Monitoring](../deployment/MONITORING_SETUP.md)

## 📞 Support & Resources

### **Documentation**
- [Architecture Documentation](../architecture/)
- [Module Documentation](../modules/)
- [API Documentation](../api/)
- [Deployment Documentation](../deployment/)

### **Development Resources**
- [Code Style Guide](CODE_STYLE.md)
- [Testing Guide](TESTING_GUIDE.md)
- [Debugging Guide](DEBUGGING_GUIDE.md)

### **Community**
- Check existing issues and documentation
- Follow coding standards and best practices
- Write tests for new functionality
- Document your changes

---

*Welcome to the Flask Credit System! This modular architecture provides a solid foundation for building scalable, maintainable applications. Happy coding! 🚀* 