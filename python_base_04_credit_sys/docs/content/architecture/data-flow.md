# Data Flow

How data flows through the Credit System application.

## Request Flow

1. **API Request** → Rate Limiter
2. **Authentication** → JWT Manager
3. **Authorization** → API Key Manager
4. **Business Logic** → Module Manager
5. **Data Access** → Database Manager
6. **Caching** → Redis Manager
7. **Response** → Client

## Dependencies

### app
- `os`
- `core.managers.app_manager.AppManager`
- `utils.config.config.Config`
- `sys`
- `flask_cors.CORS`
- `tools.logger.custom_logging.custom_log`
- `core.metrics.init_metrics`
- `flask.Flask`
- `importlib`

### None
- `typing.Callable`
- `vault_manager.VaultManager`
- `custom_logging.custom_log`
- `prometheus_flask_exporter.PrometheusMetrics`
- `requests`
- `typing.Any`
- `app_manager.AppManager`
- `tools.logger.custom_logging.custom_log`
- `jwt_manager.JWTManager`
- `communications_main.CommunicationsModule`
- `prometheus_client.Histogram`
- `core.managers.database_manager.DatabaseManager`
- `importlib`
- `typing.List`
- `core.managers.redis_manager.RedisManager`
- `datetime.timedelta`
- `core.managers.app_manager.AppManager`
- `typing.Optional`
- `exceptions.validation_exceptions.ValidationError`
- `prometheus_client.Gauge`
- `transactions_main.TransactionsModule`
- `prometheus_client.Counter`
- `enum.Enum`
- `service_manager.ServicesManager`
- `flask_cors.CORS`
- `base64`
- `typing.Dict`
- `encryption_manager.EncryptionManager`
- `html`
- `re`
- `cryptography.fernet.Fernet`
- `json`
- `datetime.datetime`
- `rate_limiter_manager.RateLimiterManager`
- `error_handler.ErrorHandler`
- `typing.Union`
- `redis_manager.RedisManager`
- `cryptography.hazmat.primitives.hashes`
- `sys`
- `wallet_main.WalletModule`
- `gzip`
- `abc.ABC`
- `flask.Flask`
- `custom_logging.sanitize_log_message`
- `database_manager.DatabaseManager`
- `os`
- `cs_user_management_main.CSUserManagementModule`
- `logging`
- `traceback`
- `hooks_manager.HooksManager`
- `utils.config.config.Config`
- `abc.abstractmethod`
- `config.config.Config`
- `glob`
- `psycopg2`
- `core.metrics.init_metrics`
- `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC`
- `module_manager.ModuleManager`

### tools.logger.audit_logger
- `os`
- `datetime.datetime`
- `json`
- `typing.Optional`
- `custom_logging.custom_log`
- `glob`
- `typing.Any`
- `gzip`
- `typing.Dict`
- `custom_logging.sanitize_log_message`

### tools.error_handling.error_handler
- `datetime.datetime`
- `logging`
- `typing.Optional`
- `traceback`
- `typing.Any`
- `psycopg2`
- `tools.logger.custom_logging.custom_log`
- `typing.Dict`
- `re`

### core.metrics
- `utils.config.config.Config`
- `prometheus_client.Gauge`
- `prometheus_client.Counter`
- `prometheus_flask_exporter.PrometheusMetrics`
- `prometheus_client.Histogram`
- `flask.Flask`

### core.managers.state_manager
- `datetime.datetime`
- `logging`
- `typing.Optional`
- `typing.Callable`
- `enum.Enum`
- `typing.Any`
- `tools.logger.custom_logging.custom_log`
- `typing.Dict`
- `core.managers.database_manager.DatabaseManager`
- `typing.List`
- `core.managers.redis_manager.RedisManager`

### core.managers.vault_manager
- `json`
- `os`
- `datetime.datetime`
- `datetime.timedelta`
- `logging`
- `typing.Optional`
- `requests`
- `typing.Any`
- `typing.Dict`

### core.managers.secret_manager
- `os`

### core.managers.encryption_manager
- `os`
- `typing.Optional`
- `utils.config.config.Config`
- `cryptography.hazmat.primitives.hashes`
- `typing.Any`
- `base64`
- `typing.Dict`
- `cryptography.hazmat.primitives.kdf.pbkdf2.PBKDF2HMAC`
- `cryptography.fernet.Fernet`

### core.modules.base_module
- `logging`
- `typing.Optional`
- `abc.abstractmethod`
- `typing.Any`
- `tools.logger.custom_logging.custom_log`
- `typing.Dict`
- `abc.ABC`
- `typing.List`

### utils.validation.payload_validator
- `json`
- `exceptions.validation_exceptions.ValidationError`
- `typing.Union`
- `config.config.Config`
- `typing.Any`
- `typing.Dict`
- `typing.List`

### utils.validation.sanitizer
- `exceptions.validation_exceptions.ValidationError`
- `typing.Union`
- `config.config.Config`
- `typing.Any`
- `html`
- `typing.Dict`
- `re`
- `typing.List`

