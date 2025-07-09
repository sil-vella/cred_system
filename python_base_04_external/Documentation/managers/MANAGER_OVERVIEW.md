# Core Managers Overview

## 🏗️ Introduction

Core Managers are the infrastructure layer of the Flask Credit System, providing specialized services to modules and handling cross-cutting concerns. Each manager is responsible for a specific aspect of the system's infrastructure.

## 📋 Manager Hierarchy

```
AppManager (Central Orchestrator)
├── ModuleManager           # Module lifecycle management
├── DatabaseManager         # MongoDB operations  
├── RedisManager           # Redis caching & sessions
├── JWTManager             # JSON Web Token handling
├── EncryptionManager      # Data encryption/decryption
├── VaultManager           # HashiCorp Vault integration
├── RateLimiterManager     # Request rate limiting
├── HooksManager           # Application lifecycle hooks  
└── ServicesManager        # External service integrations
```

## ⚙️ Manager Responsibilities

### **1. AppManager** - Central Orchestrator
**Purpose**: Main application controller and dependency coordinator

**Key Features**:
- Flask application initialization
- Manager coordination and lifecycle
- Module system integration
- Health check aggregation
- Route registration and middleware setup

**Usage**:
```python
# Primary entry point
app_manager = AppManager()
app_manager.initialize()
app_manager.run()
```

---

### **2. ModuleManager** - Module Lifecycle
**Purpose**: Manages module discovery, initialization, and runtime operations

**Key Features**:
- Automatic module discovery in `core/modules/`
- Dependency resolution and load ordering
- Module initialization and health monitoring
- Inter-module communication facilitation

**Usage**:
```python
# Access modules
module_manager = app_manager.module_manager
wallet_module = module_manager.get_module('wallet_module')

# Check module health
health = module_manager.get_module_health('wallet_module')
status = module_manager.get_module_status()
```

---

### **3. DatabaseManager** - MongoDB Operations
**Purpose**: Handles all MongoDB database operations and connection management

**Key Features**:
- Connection pooling and management
- Database and collection operations
- Query optimization and monitoring
- Error handling and reconnection logic
- **Deterministic encryption for searchable fields** (see below)

**Deterministic Encryption for Searchable Fields**:
- When storing or searching for fields like `email` or `username`, the DatabaseManager uses deterministic encryption (hash-based) so that the same input always produces the same encrypted output.
- This allows secure storage of sensitive data while still enabling login and user lookup by email/username.
- All other sensitive fields use standard (randomized) encryption for maximum security.

---

### **4. RedisManager** - Caching & Sessions
**Purpose**: Manages Redis operations for caching, sessions, and temporary data

**Key Features**:
- Connection management and pooling
- Caching strategies (TTL, eviction policies)
- Session storage and management
- Rate limiting data storage

**Usage**:
```python
# Caching operations
redis = app_manager.redis_manager
redis.set('user:123', user_data, ttl=3600)
cached_user = redis.get('user:123')

# Session management
redis.set_session(session_id, session_data)
session = redis.get_session(session_id)
```

---

### **5. JWTManager** - Authentication Tokens
**Purpose**: Handles JWT token creation, validation, and management

**Key Features**:
- Token generation and signing
- Token validation and expiration handling
- Refresh token management
- Claims validation and extraction

**Usage**:
```python
# Token operations
jwt = app_manager.jwt_manager
token = jwt.generate_token(user_id="123", role="user")
payload = jwt.validate_token(token)
is_valid = jwt.is_token_valid(token)
```

---

### **6. EncryptionManager** - Data Security
**Purpose**: Provides field-level encryption for sensitive data

**Key Features**:
- Fernet-based symmetric encryption
- Key management and rotation
- Automatic encryption/decryption of sensitive fields
- Secure key storage integration
- **Deterministic encryption for searchable fields** (see below)

**Deterministic Encryption for Searchable Fields**:
- For fields that must be searched (like `email` and `username`), the EncryptionManager uses a hash-based deterministic encryption method.
- This ensures that searching for a user by email or username works, even though the data is encrypted at rest.
- For all other fields, standard encryption with random IVs is used for maximum security.
- This approach resolves issues where login or user lookup would fail due to non-deterministic encryption.

---

### **7. VaultManager** - Secrets Management
**Purpose**: Integrates with HashiCorp Vault for secure secrets management

**Key Features**:
- AppRole authentication with Vault
- Dynamic secret retrieval
- Secret caching and refresh
- Secure configuration management

**Usage**:
```python
# Secret operations
vault = app_manager.vault_manager
db_password = vault.get_secret("database", "password")
api_key = vault.get_secret("external_service", "api_key")

# Configuration retrieval
config = vault.get_all_secrets("app_config")
```

---

### **8. RateLimiterManager** - Request Throttling
**Purpose**: Implements rate limiting to prevent abuse and ensure fair usage

**Key Features**:
- Per-user and per-IP rate limiting
- Sliding window and token bucket algorithms
- Redis-backed rate limit storage
- Configurable rate limit policies

**Usage**:
```python
# Rate limiting
rate_limiter = app_manager.rate_limiter_manager
is_allowed = rate_limiter.is_request_allowed(user_id="123", endpoint="/api/transfer")
rate_limiter.record_request(user_id="123", endpoint="/api/transfer")
```

---

### **9. HooksManager** - Lifecycle Events
**Purpose**: Manages application lifecycle hooks and event handling

**Key Features**:
- Pre/post request hooks
- Module lifecycle events
- Custom event registration and handling
- Async event processing

**Usage**:
```python
# Hook registration
hooks = app_manager.hooks_manager
hooks.register_hook('before_request', validate_auth)
hooks.register_hook('after_module_init', setup_monitoring)

# Event triggering
hooks.trigger('custom_event', data=event_data)
```

---

### **10. ServicesManager** - External Integrations
**Purpose**: Manages integrations with external services and APIs

**Key Features**:
- HTTP client management
- Service discovery and load balancing
- Circuit breaker patterns for resilience
- Request/response logging and monitoring

**Usage**:
```python
# External service calls
services = app_manager.services_manager
response = services.call('payment_service', 'POST', '/process', data=payment_data)
health = services.health_check('notification_service')
```

## 🔗 Manager Interaction Patterns

### **Dependency Injection**
Managers are provided to modules through the app_manager:

```python
class MyModule(BaseModule):
    def initialize(self, app_manager) -> bool:
        # Access any manager
        self.db = app_manager.database_manager
        self.redis = app_manager.redis_manager
        self.jwt = app_manager.jwt_manager
        return True
```

### **Manager Communication**
Managers can interact with each other through the app_manager:

```python
class DatabaseManager:
    def __init__(self, app_manager):
        self.app_manager = app_manager
        
    def get_cached_query(self, query_key, query_func):
        # Use redis manager for caching
        redis = self.app_manager.redis_manager
        cached = redis.get(query_key)
        if cached:
            return cached
            
        result = query_func()
        redis.set(query_key, result, ttl=300)
        return result
```

## 📊 Manager Configuration

### **Configuration Priority**
All managers follow the configuration hierarchy:
1. **Vault Secrets** (highest priority)
2. **Configuration Files**  
3. **Environment Variables**
4. **Default Values** (lowest priority)

### **Common Configuration Pattern**
```python
class MyManager:
    def __init__(self, app_manager):
        self.config = self._load_config(app_manager)
        
    def _load_config(self, app_manager):
        vault = app_manager.vault_manager
        
        return {
            'setting1': vault.get_secret('my_manager', 'setting1') or 
                       os.getenv('MY_MANAGER_SETTING1', 'default_value'),
            'setting2': vault.get_secret('my_manager', 'setting2') or
                       os.getenv('MY_MANAGER_SETTING2', 'default_value')
        }
```

## 🔍 Manager Health Monitoring

### **Health Check Interface**
All managers implement health checking:

```python
class MyManager:
    def health_check(self) -> dict:
        return {
            "manager": "my_manager",
            "status": "healthy" if self._is_healthy() else "unhealthy",
            "connections": self._check_connections(),
            "performance": self._get_performance_metrics(),
            "last_check": datetime.utcnow().isoformat()
        }
```

### **System Health Aggregation**
AppManager aggregates all manager health checks:

```python
# Access via endpoint
GET /health

# Response includes all manager statuses
{
    "status": "healthy",
    "managers": {
        "database": {"status": "healthy", "connection": "ok"},
        "redis": {"status": "healthy", "connection": "ok"},
        "vault": {"status": "unhealthy", "error": "connection_failed"}
    },
    "modules": {
        "wallet": {"status": "healthy"},
        "transactions": {"status": "healthy"}
    }
}
```

## 🛠️ Manager Development

### **Creating New Managers**
When creating new managers, follow this pattern:

```python
# core/managers/my_new_manager.py
from tools.logger.custom_logger import custom_log
from datetime import datetime

class MyNewManager:
    def __init__(self, app_manager):
        self.app_manager = app_manager
        self.config = self._load_config()
        self.initialized = False
        
    def initialize(self) -> bool:
        """Initialize the manager"""
        try:
            # Initialization logic
            custom_log(f"Initializing MyNewManager...")
            self.initialized = True
            custom_log(f"✅ MyNewManager initialized successfully")
            return True
        except Exception as e:
            custom_log(f"❌ Failed to initialize MyNewManager: {e}")
            return False
    
    def health_check(self) -> dict:
        """Return manager health status"""
        return {
            "manager": "my_new_manager",
            "status": "healthy" if self.initialized else "unhealthy",
            "initialized": self.initialized,
            "last_check": datetime.utcnow().isoformat()
        }
    
    def dispose(self):
        """Cleanup resources"""
        custom_log(f"Disposing MyNewManager...")
        self.initialized = False
```

### **Manager Registration**
Add new managers to AppManager:

```python
# core/managers/app_manager.py
class AppManager:
    def __init__(self):
        # Existing managers...
        self.my_new_manager = MyNewManager(self)
        
    def initialize_managers(self):
        # Initialize new manager
        if not self.my_new_manager.initialize():
            raise Exception("Failed to initialize MyNewManager")
```

## 📈 Performance Considerations

### **Manager Initialization Order**
Critical managers initialize first:
1. Configuration/Vault Manager
2. Database Manager  
3. Redis Manager
4. Other managers (parallel where possible)
5. Module Manager (last)

### **Resource Management**
- **Connection Pooling**: Database and Redis use connection pools
- **Lazy Loading**: Expensive operations deferred until needed
- **Resource Cleanup**: Proper disposal methods for all managers
- **Memory Management**: Efficient caching and cleanup strategies

## 🚀 Future Manager Development

### **Planned Managers**
- **MetricsManager**: Prometheus metrics collection
- **LoggingManager**: Centralized logging management  
- **ConfigManager**: Enhanced configuration management
- **CacheManager**: Advanced caching strategies
- **SecurityManager**: Security policy enforcement

### **Manager Best Practices**
1. **Single Responsibility**: Each manager handles one concern
2. **Loose Coupling**: Managers interact through well-defined interfaces
3. **Error Handling**: Graceful failure and recovery mechanisms
4. **Monitoring**: Comprehensive health checks and metrics
5. **Documentation**: Clear API documentation and usage examples

---

*Core Managers provide the foundation for the Flask Credit System's infrastructure, enabling modules to focus on business logic while leveraging robust, well-tested infrastructure services.* 