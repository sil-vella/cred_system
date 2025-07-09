# Flask Credit System Documentation

## 📋 Table of Contents

### 🏗️ [Architecture](./architecture/)
- [System Overview](./architecture/SYSTEM_OVERVIEW.md) - High-level architecture and design principles
- [Module-First Architecture](./architecture/MODULE_FIRST_ARCHITECTURE.md) - Core architectural pattern
- [Data Flow](./architecture/DATA_FLOW.md) - Request/response flow through the system
- [Security Architecture](./architecture/SECURITY_ARCHITECTURE.md) - Security layers and implementation

### 🧩 [Modules](./modules/)
- [Module System Overview](./modules/MODULE_SYSTEM.md) - How the module system works
- [Base Module](./modules/BASE_MODULE.md) - Abstract base class for all modules
- [Connection API](./modules/communications_module.md) - Core database and API operations
- [User Management](./modules/USER_MANAGEMENT.md) - User authentication and management
- [Wallet Module](./modules/WALLET_MODULE.md) - Credit balance management
- [Transactions Module](./modules/TRANSACTIONS_MODULE.md) - Transaction processing

### ⚙️ [Core Managers](./managers/)
- [Manager Overview](./managers/MANAGER_OVERVIEW.md) - Core manager responsibilities
- [App Manager](./managers/APP_MANAGER.md) - Central application orchestrator
- [Module Manager](./managers/MODULE_MANAGER.md) - Module lifecycle management
- [Database Manager](./managers/DATABASE_MANAGER.md) - MongoDB operations
- [Redis Manager](./managers/REDIS_MANAGER.md) - Redis caching and sessions
- [Vault Manager](./managers/VAULT_MANAGER.md) - HashiCorp Vault integration
- [JWT Manager](./managers/JWT_MANAGER.md) - JSON Web Token management
- [Encryption Manager](./managers/ENCRYPTION_MANAGER.md) - Data encryption/decryption

### 🔧 [Development](./development/)
- [Getting Started](./development/GETTING_STARTED.md) - Development environment setup
- [Module Development](./development/MODULE_DEVELOPMENT.md) - Creating new modules
- [Testing Guide](./development/TESTING_GUIDE.md) - Testing strategies and tools
- [Code Style](./development/CODE_STYLE.md) - Coding standards and best practices
- [Debugging Guide](./development/DEBUGGING_GUIDE.md) - Debugging and troubleshooting

### 📡 [API Documentation](./api/)
- [API Overview](./api/API_OVERVIEW.md) - REST API structure and conventions
- [Authentication Endpoints](./api/AUTHENTICATION.md) - User auth and JWT endpoints
- [User Endpoints](./api/USER_ENDPOINTS.md) - User management operations  
- [Wallet Endpoints](./api/WALLET_ENDPOINTS.md) - Credit balance operations
- [Transaction Endpoints](./api/TRANSACTION_ENDPOINTS.md) - Transaction management
- [System Endpoints](./api/SYSTEM_ENDPOINTS.md) - Health checks and system status

### 🚀 [Deployment](./deployment/)
- [Deployment Overview](./deployment/DEPLOYMENT_OVERVIEW.md) - Deployment strategies
- [Docker Guide](./deployment/DOCKER_GUIDE.md) - Container deployment
- [Kubernetes Guide](./deployment/KUBERNETES_GUIDE.md) - K8s deployment
- [Environment Configuration](./deployment/ENVIRONMENT_CONFIG.md) - Environment variables
- [Monitoring Setup](./deployment/MONITORING_SETUP.md) - Metrics and logging

### 🔄 [Migration](./migration/)
- [Plugin to Module Migration](./migration/PLUGIN_TO_MODULE_MIGRATION.md) - Refactoring history
- [Breaking Changes](./migration/BREAKING_CHANGES.md) - Version compatibility
- [Upgrade Guide](./migration/UPGRADE_GUIDE.md) - How to upgrade existing deployments

## 🚀 Quick Start

1. **Development**: Start with [Getting Started](./development/GETTING_STARTED.md)
2. **Understanding Architecture**: Read [System Overview](./architecture/SYSTEM_OVERVIEW.md)
3. **Creating Modules**: Follow [Module Development](./development/MODULE_DEVELOPMENT.md)
4. **API Usage**: Check [API Overview](./api/API_OVERVIEW.md)
5. **Deployment**: Use [Deployment Overview](./deployment/DEPLOYMENT_OVERVIEW.md)

## 📈 System Status

- **Architecture**: Module-First ✅
- **Plugin System**: Deprecated ❌ → Removed ✅
- **Modules Active**: 4 (communications_module, user_management, wallet, transactions)
- **Documentation Coverage**: Complete ✅
- **Production Ready**: Yes ✅

---

*Last Updated: $(date '+%Y-%m-%d')*
*Architecture Version: Module-First v1.0* 

---

## 🔒 Update: Deterministic Encryption for Searchable Fields (2025-07-09)

- The authentication and user management system now uses deterministic encryption for searchable fields (such as `email` and `username`).
- This allows secure storage of sensitive data while still enabling login and user lookup by email/username.
- The encryption manager uses a hash-based deterministic encryption for these fields, while all other sensitive fields use standard (randomized) encryption.
- This change resolves previous issues where login failed due to non-deterministic encryption of emails.
- See the [Manager Overview](./managers/MANAGER_OVERVIEW.md) and [User Authentication System](./architecture/USER_AUTHENTICATION_SYSTEM.md) for details. 