import os
import logging

# Initialize logger for config
logger = logging.getLogger(__name__)

# Global VaultManager instance (initialized once)
_vault_manager = None

def get_vault_manager():
    """Get or create VaultManager instance with error handling."""
    global _vault_manager
    if _vault_manager is None:
        try:
            from core.managers.vault_manager import VaultManager
            _vault_manager = VaultManager()
            logger.info("✅ VaultManager initialized successfully for config")
        except Exception as e:
            logger.warning(f"⚠️ VaultManager initialization failed: {e}")
            _vault_manager = False  # Mark as failed to avoid retrying
    return _vault_manager if _vault_manager is not False else None

# Helper to read secrets from files (returns None if not found)
def read_secret_file(secret_name: str) -> str:
    """Read secret from file system."""
    path = f"/run/secrets/{secret_name}"
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except Exception:
        return None

def get_vault_secret(path: str, key: str) -> str:
    """Get secret from Vault with error handling."""
    try:
        vault = get_vault_manager()
        if vault:
            return vault.get_secret_value(path, key)
    except Exception as e:
        logger.debug(f"Failed to get vault secret {path}/{key}: {e}")
    return None

def get_config_value(vault_path: str, vault_key: str, file_name: str = None, env_name: str = None, default_value: str = ""):
    """
    Get configuration value with priority: Vault > File > Environment > Default
    
    Args:
        vault_path: Vault secret path (e.g., 'flask-app/mongodb')
        vault_key: Key within the vault secret (e.g., 'database_name')
        file_name: Secret file name (optional)
        env_name: Environment variable name (optional)
        default_value: Default value if all sources fail
    """
    # Skip Vault during initial class loading to avoid circular imports
    # Vault will be available after full app initialization
    
    # 1. Try secret file first (during initialization)
    if file_name:
        file_value = read_secret_file(file_name)
        if file_value is not None:
            return file_value
    
    # 2. Try environment variable
    if env_name:
        env_value = os.getenv(env_name)
        if env_value is not None:
            return env_value
    
    # 3. Try Vault (only after app is fully loaded)
    if vault_path and vault_key:
        try:
            vault_value = get_vault_secret(vault_path, vault_key)
            if vault_value is not None:
                return vault_value
        except:
            pass  # Ignore Vault errors during initialization
    
    # 4. Return default value
    return default_value

class Config:
    # Flask Configuration
    FLASK_SERVICE_NAME = get_config_value("flask-app/app", "service_name", "flask_service_name", "FLASK_SERVICE_NAME", "flask")
    FLASK_PORT = int(get_config_value("flask-app/app", "port", "flask_port", "FLASK_PORT", "5000"))
    PYTHONPATH = get_config_value(None, None, "pythonpath", "PYTHONPATH", "/app")
    FLASK_ENV = get_config_value("flask-app/app", "environment", None, "FLASK_ENV", "development")

    # Vault Configuration
    VAULT_TOKEN_FILE = read_secret_file("vault_token_file") or os.getenv("VAULT_TOKEN_FILE", "/vault/secrets/token")
    DB_CREDS_FILE = read_secret_file("db_creds_file") or os.getenv("DB_CREDS_FILE", "/vault/secrets/flask-creds")
    VAULT_ADDR = os.getenv("VAULT_ADDR", "http://vault-proxy:8200")
    VAULT_AUTH_PATH = os.getenv("VAULT_AUTH_PATH", "auth/kubernetes")
    VAULT_ROLE = os.getenv("VAULT_ROLE", "flask-app")

    # MongoDB Configuration (now Vault-first)
    MONGODB_SERVICE_NAME = get_config_value("flask-app/mongodb", "service_name", "mongodb_service_name", "MONGODB_SERVICE_NAME", "mongodb")
    MONGODB_ROOT_USER = get_config_value("flask-app/mongodb", "root_user", "mongodb_root_user", "MONGODB_ROOT_USER", "root")
    MONGODB_ROOT_PASSWORD = get_config_value("flask-app/mongodb", "root_password", "mongodb_root_password", "MONGODB_ROOT_PASSWORD", "rootpassword")
    MONGODB_USER = get_config_value("flask-app/mongodb", "user", "mongodb_user", "MONGODB_USER", "credit_system_user")
    MONGODB_PASSWORD = get_config_value("flask-app/mongodb", "user_password", "mongodb_user_password", "MONGODB_PASSWORD", "credit_system_password")
    MONGODB_DB_NAME = get_config_value("flask-app/mongodb", "database_name", "mongodb_db_name", "MONGODB_DB_NAME", "credit_system")
    MONGODB_PORT = int(get_config_value("flask-app/mongodb", "port", "mongodb_port", "MONGODB_PORT", "27017"))

    # Redis Configuration (now Vault-first)
    REDIS_SERVICE_NAME = get_config_value("flask-app/redis", "service_name", "redis_service_name", "REDIS_SERVICE_NAME", "redis")
    REDIS_HOST = get_config_value("flask-app/redis", "host", None, "REDIS_HOST", "redis-master.flask-app.svc.cluster.local")
    REDIS_PORT = int(get_config_value("flask-app/redis", "port", None, "REDIS_PORT", "6379"))
    REDIS_PASSWORD = get_config_value("flask-app/redis", "password", None, "REDIS_PASSWORD", "")
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_USE_SSL = os.getenv("REDIS_USE_SSL", "false").lower() == "true"
    REDIS_SSL_VERIFY_MODE = os.getenv("REDIS_SSL_VERIFY_MODE", "required")
    REDIS_SOCKET_TIMEOUT = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
    REDIS_SOCKET_CONNECT_TIMEOUT = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
    REDIS_RETRY_ON_TIMEOUT = os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
    REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))
    REDIS_MAX_RETRIES = int(os.getenv("REDIS_MAX_RETRIES", "3"))
    RATE_LIMIT_STORAGE_URL = os.getenv("RATE_LIMIT_STORAGE_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")

    # Debug mode (now Vault-first)
    DEBUG = get_config_value("flask-app/app", "debug", None, "FLASK_DEBUG", "False").lower() in ("true", "1")

    # App URL Configuration
    APP_URL = os.getenv("APP_URL", "http://localhost:5000")

    # External Credit System Configuration
    CREDIT_SYSTEM_URL = os.getenv("CREDIT_SYSTEM_URL", "http://localhost:8000")
    CREDIT_SYSTEM_API_KEY = os.getenv("CREDIT_SYSTEM_API_KEY", "test_api_key")

    # JWT Configuration (now Vault-first for secret key)
    JWT_SECRET_KEY = get_config_value("flask-app/app", "secret_key", None, "JWT_SECRET_KEY", "your-super-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "3600"))  # 1 hour in seconds
    JWT_REFRESH_TOKEN_EXPIRES = int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", "604800"))  # 7 days in seconds
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_TOKEN_TYPE = os.getenv("JWT_TOKEN_TYPE", "bearer")
    JWT_HEADER_NAME = os.getenv("JWT_HEADER_NAME", "Authorization")
    JWT_HEADER_TYPE = os.getenv("JWT_HEADER_TYPE", "Bearer")
    JWT_QUERY_STRING_NAME = os.getenv("JWT_QUERY_STRING_NAME", "token")
    JWT_QUERY_STRING_VALUE_PREFIX = os.getenv("JWT_QUERY_STRING_VALUE_PREFIX", "Bearer")
    JWT_COOKIE_NAME = os.getenv("JWT_COOKIE_NAME", "access_token")
    JWT_COOKIE_CSRF_PROTECT = os.getenv("JWT_COOKIE_CSRF_PROTECT", "true").lower() == "true"
    JWT_COOKIE_SECURE = os.getenv("JWT_COOKIE_SECURE", "true").lower() == "true"
    JWT_COOKIE_SAMESITE = os.getenv("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_DOMAIN = os.getenv("JWT_COOKIE_DOMAIN", None)
    JWT_COOKIE_PATH = os.getenv("JWT_COOKIE_PATH", "/")
    JWT_COOKIE_MAX_AGE = int(os.getenv("JWT_COOKIE_MAX_AGE", "3600"))  # 1 hour in seconds

    # Toggle SSL for PostgreSQL
    USE_SSL = os.getenv("USE_SSL", "False").lower() in ("true", "1")

    # Database Pool Configuration
    DB_POOL_MIN_CONN = int(os.getenv("DB_POOL_MIN_CONN", "1"))
    DB_POOL_MAX_CONN = int(os.getenv("DB_POOL_MAX_CONN", "10"))
    
    # Connection Pool Security Settings
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))  # Connection timeout in seconds
    DB_STATEMENT_TIMEOUT = int(os.getenv("DB_STATEMENT_TIMEOUT", "30000"))  # Statement timeout in milliseconds
    DB_KEEPALIVES = int(os.getenv("DB_KEEPALIVES", "1"))  # Enable keepalive
    DB_KEEPALIVES_IDLE = int(os.getenv("DB_KEEPALIVES_IDLE", "30"))  # Idle timeout in seconds
    DB_KEEPALIVES_INTERVAL = int(os.getenv("DB_KEEPALIVES_INTERVAL", "10"))  # Keepalive interval in seconds
    DB_KEEPALIVES_COUNT = int(os.getenv("DB_KEEPALIVES_COUNT", "5"))
    DB_MAX_CONNECTIONS_PER_USER = int(os.getenv("DB_MAX_CONNECTIONS_PER_USER", "5"))  # Maximum connections per user
    
    # Resource Protection
    DB_MAX_QUERY_SIZE = int(os.getenv("DB_MAX_QUERY_SIZE", "10000"))  # Maximum query size in bytes
    DB_MAX_RESULT_SIZE = int(os.getenv("DB_MAX_RESULT_SIZE", "1048576"))  # Maximum result size in bytes (1MB)
    
    # Connection Retry Settings
    DB_RETRY_COUNT = int(os.getenv("DB_RETRY_COUNT", "3"))  # Number of connection retry attempts
    DB_RETRY_DELAY = int(os.getenv("DB_RETRY_DELAY", "1"))  # Delay between retries in seconds
    
    # Flask-Limiter: Redis backend for rate limiting
    RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
    RATE_LIMIT_IP_REQUESTS = int(os.getenv("RATE_LIMIT_IP_REQUESTS", "100"))  # Requests per window
    RATE_LIMIT_IP_WINDOW = int(os.getenv("RATE_LIMIT_IP_WINDOW", "60"))  # Window in seconds
    RATE_LIMIT_IP_PREFIX = os.getenv("RATE_LIMIT_IP_PREFIX", "rate_limit:ip")
    RATE_LIMIT_USER_REQUESTS = int(os.getenv("RATE_LIMIT_USER_REQUESTS", "1000"))  # Requests per window
    RATE_LIMIT_USER_WINDOW = int(os.getenv("RATE_LIMIT_USER_WINDOW", "3600"))  # Window in seconds
    RATE_LIMIT_USER_PREFIX = os.getenv("RATE_LIMIT_USER_PREFIX", "rate_limit:user")
    RATE_LIMIT_API_KEY_REQUESTS = int(os.getenv("RATE_LIMIT_API_KEY_REQUESTS", "10000"))  # Requests per window
    RATE_LIMIT_API_KEY_WINDOW = int(os.getenv("RATE_LIMIT_API_KEY_WINDOW", "3600"))  # Window in seconds
    RATE_LIMIT_API_KEY_PREFIX = os.getenv("RATE_LIMIT_API_KEY_PREFIX", "rate_limit:api_key")
    RATE_LIMIT_HEADERS_ENABLED = os.getenv("RATE_LIMIT_HEADERS_ENABLED", "true").lower() == "true"
    RATE_LIMIT_HEADER_LIMIT = "X-RateLimit-Limit"
    RATE_LIMIT_HEADER_REMAINING = "X-RateLimit-Remaining"
    RATE_LIMIT_HEADER_RESET = "X-RateLimit-Reset"

    # Auto-ban Configuration
    AUTO_BAN_ENABLED = os.getenv("AUTO_BAN_ENABLED", "true").lower() == "true"
    AUTO_BAN_VIOLATIONS_THRESHOLD = int(os.getenv("AUTO_BAN_VIOLATIONS_THRESHOLD", "5"))  # Number of violations before ban
    AUTO_BAN_DURATION = int(os.getenv("AUTO_BAN_DURATION", "3600"))  # Ban duration in seconds (default 1 hour)
    AUTO_BAN_WINDOW = int(os.getenv("AUTO_BAN_WINDOW", "300"))  # Window to track violations (default 5 minutes)
    AUTO_BAN_PREFIX = os.getenv("AUTO_BAN_PREFIX", "ban")
    AUTO_BAN_VIOLATIONS_PREFIX = os.getenv("AUTO_BAN_VIOLATIONS_PREFIX", "violations")

    # Credit Amount Validation Settings
    CREDIT_MIN_AMOUNT = float(os.getenv("CREDIT_MIN_AMOUNT", "0.01"))  # Minimum credit amount
    CREDIT_MAX_AMOUNT = float(os.getenv("CREDIT_MAX_AMOUNT", "1000000.0"))  # Maximum credit amount
    CREDIT_PRECISION = int(os.getenv("CREDIT_PRECISION", "2"))  # Number of decimal places allowed
    CREDIT_ALLOW_NEGATIVE = os.getenv("CREDIT_ALLOW_NEGATIVE", "false").lower() == "true"

    # Transaction Validation Settings
    MAX_METADATA_SIZE = int(os.getenv("MAX_METADATA_SIZE", "1024"))  # Maximum metadata size in bytes
    MAX_REFERENCE_ID_LENGTH = int(os.getenv("MAX_REFERENCE_ID_LENGTH", "64"))  # Maximum reference ID length
    ALLOWED_TRANSACTION_TYPES = os.getenv("ALLOWED_TRANSACTION_TYPES", "purchase,reward,burn,transfer,refund").split(",")

    # Transaction Integrity Settings
    TRANSACTION_WINDOW = int(os.getenv("TRANSACTION_WINDOW", "3600"))  # Time window for replay attack prevention (in seconds)
    REQUIRE_TRANSACTION_ID = os.getenv("REQUIRE_TRANSACTION_ID", "true").lower() == "true"  # Whether transaction IDs are required
    ENFORCE_BALANCE_VALIDATION = os.getenv("ENFORCE_BALANCE_VALIDATION", "true").lower() == "true"  # Whether to enforce balance validation

    # Payload Validation Settings
    MAX_PAYLOAD_SIZE = int(os.getenv("MAX_PAYLOAD_SIZE", "1048576"))  # 1MB default
    MAX_NESTING_DEPTH = int(os.getenv("MAX_NESTING_DEPTH", "10"))  # Maximum nesting depth
    MAX_ARRAY_SIZE = int(os.getenv("MAX_ARRAY_SIZE", "1000"))  # Maximum array size
    MAX_STRING_LENGTH = int(os.getenv("MAX_STRING_LENGTH", "65536"))  # Maximum string length

    # Encryption settings
    ENCRYPTION_SALT = os.getenv("ENCRYPTION_SALT", "default_salt_123")  # Should be changed in production
    SENSITIVE_FIELDS = [
        "user_id",
        "email",
        "phone",
        "address",
        "credit_balance",
        "transaction_history"
    ]

    # MongoDB Configuration
    MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_AUTH_SOURCE = os.getenv("MONGODB_AUTH_SOURCE", "admin")
    
    # MongoDB Role-Based Access Control
    MONGODB_ROLES = {
        "admin": ["readWriteAnyDatabase", "dbAdminAnyDatabase", "userAdminAnyDatabase"],
        "read_write": ["readWrite"],
        "read_only": ["read"]
    }
    
    # MongoDB Replica Set Configuration
    MONGODB_REPLICA_SET = os.getenv("MONGODB_REPLICA_SET", "")
    MONGODB_READ_PREFERENCE = os.getenv("MONGODB_READ_PREFERENCE", "primary")
    MONGODB_READ_CONCERN = os.getenv("MONGODB_READ_CONCERN", "majority")
    MONGODB_WRITE_CONCERN = os.getenv("MONGODB_WRITE_CONCERN", "majority")
    
    # MongoDB Connection Settings
    MONGODB_MAX_POOL_SIZE = int(os.getenv("MONGODB_MAX_POOL_SIZE", "100"))
    MONGODB_MIN_POOL_SIZE = int(os.getenv("MONGODB_MIN_POOL_SIZE", "10"))
    MONGODB_MAX_IDLE_TIME_MS = int(os.getenv("MONGODB_MAX_IDLE_TIME_MS", "60000"))
    MONGODB_SOCKET_TIMEOUT_MS = int(os.getenv("MONGODB_SOCKET_TIMEOUT_MS", "5000"))
    MONGODB_CONNECT_TIMEOUT_MS = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
    
    # MongoDB SSL/TLS Settings
    MONGODB_SSL = os.getenv("MONGODB_SSL", "false").lower() == "true"
    MONGODB_SSL_CA_FILE = os.getenv("MONGODB_SSL_CA_FILE", "")
    MONGODB_SSL_CERT_FILE = os.getenv("MONGODB_SSL_CERT_FILE", "")
    MONGODB_SSL_KEY_FILE = os.getenv("MONGODB_SSL_KEY_FILE", "")
    MONGODB_SSL_ALLOW_INVALID_CERTIFICATES = os.getenv("MONGODB_SSL_ALLOW_INVALID_CERTIFICATES", "false").lower() == "true"

    @classmethod
    def refresh_from_vault(cls):
        """Refresh configuration values from Vault after app initialization."""
        try:
            vault = get_vault_manager()
            if not vault:
                logger.warning("VaultManager not available for refresh")
                return False
            
            # Refresh MongoDB config
            mongodb_secrets = vault.get_mongodb_secrets()
            if mongodb_secrets:
                cls.MONGODB_SERVICE_NAME = mongodb_secrets.get('service_name', cls.MONGODB_SERVICE_NAME)
                cls.MONGODB_ROOT_USER = mongodb_secrets.get('root_user', cls.MONGODB_ROOT_USER)
                cls.MONGODB_ROOT_PASSWORD = mongodb_secrets.get('root_password', cls.MONGODB_ROOT_PASSWORD)
                cls.MONGODB_USER = mongodb_secrets.get('user', cls.MONGODB_USER)
                cls.MONGODB_PASSWORD = mongodb_secrets.get('user_password', cls.MONGODB_PASSWORD)
                cls.MONGODB_DB_NAME = mongodb_secrets.get('database_name', cls.MONGODB_DB_NAME)
                cls.MONGODB_PORT = int(mongodb_secrets.get('port', cls.MONGODB_PORT))
                logger.info("✅ MongoDB config refreshed from Vault")
            
            # Refresh Redis config
            redis_secrets = vault.get_redis_secrets()
            if redis_secrets:
                cls.REDIS_SERVICE_NAME = redis_secrets.get('service_name', cls.REDIS_SERVICE_NAME)
                cls.REDIS_HOST = redis_secrets.get('host', cls.REDIS_HOST)
                cls.REDIS_PORT = int(redis_secrets.get('port', cls.REDIS_PORT))
                cls.REDIS_PASSWORD = redis_secrets.get('password', cls.REDIS_PASSWORD)
                logger.info("✅ Redis config refreshed from Vault")
            
            # Refresh Flask app config
            app_secrets = vault.get_app_secrets()
            if app_secrets:
                cls.JWT_SECRET_KEY = app_secrets.get('secret_key', cls.JWT_SECRET_KEY)
                cls.FLASK_ENV = app_secrets.get('environment', cls.FLASK_ENV)
                cls.DEBUG = app_secrets.get('debug', str(cls.DEBUG)).lower() in ('true', '1')
                logger.info("✅ Flask app config refreshed from Vault")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to refresh config from Vault: {e}")
            return False

    @classmethod
    def get_vault_status(cls):
        """Get current Vault integration status for debugging."""
        try:
            vault = get_vault_manager()
            if vault:
                return {
                    "status": "connected",
                    "connection_info": vault.get_connection_info(),
                    "health": vault.health_check()
                }
            else:
                return {
                    "status": "unavailable",
                    "reason": "VaultManager initialization failed or not configured"
                }
        except Exception as e:
            return {
                "status": "error",
                "reason": f"Error getting vault status: {e}"
            }
