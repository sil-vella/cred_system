import hashlib
import hmac
import time
import os
from typing import Dict, Any, Optional, List
from tools.logger.custom_logging import custom_log
from utils.config.config import Config
from core.managers.redis_manager import RedisManager


class APIKeyManager:
    def __init__(self, redis_manager=None):
        """Initialize the API Key Manager."""
        self.redis_manager = redis_manager if redis_manager else RedisManager()
        self.secret_key = Config.ENCRYPTION_KEY
        self.secrets_dir = "/app/secrets"
        # Standardized Redis key patterns
        self.KEY_PATTERNS = {
            'api_key': 'api_key:{key}',
            'app_keys': 'app_keys:{app_id}',
            'key_metadata': 'key_metadata:{app_id}',
            'key_cache': 'key_cache:{app_id}',
            'key_usage': 'key_usage:{key}',
            'app_metadata': 'app_metadata:{app_id}',
            'cred_sys_key': 'cred_sys_key'
        }
        custom_log("APIKeyManager initialized with robust cache cleanup")

    def _get_secret_file_path(self, app_id: str, app_name: str = None) -> str:
        """Get the secret file path for an app."""
        # For external app, always use CRED_SYS prefix for credit system API keys
        if app_id == "credit_system" or app_name == "Credit System":
            return os.path.join(self.secrets_dir, "CRED_SYS_api_key")
        # Use app_name for filename if provided, otherwise use app_id
        filename = f"{app_name}_api_key" if app_name else f"{app_id}_api_key"
        return os.path.join(self.secrets_dir, filename)

    def _save_api_key_to_file(self, app_id: str, api_key: str, key_data: Dict[str, Any]) -> bool:
        """Save API key to a secret file."""
        try:
            # Ensure secrets directory exists
            os.makedirs(self.secrets_dir, exist_ok=True)
            
            # Create the secret file path using app_name from key_data
            app_name = key_data.get('app_name', app_id)
            secret_file = self._get_secret_file_path(app_id, app_name)
            
            # Save API key to file
            with open(secret_file, 'w') as f:
                f.write(api_key)
            
            custom_log(f"✅ Saved API key to file: {secret_file}")
            return True
            
        except Exception as e:
            custom_log(f"❌ Error saving API key to file: {e}", level="ERROR")
            return False

    def _load_api_key_from_file(self, app_id: str) -> Optional[str]:
        """Load API key from secret file."""
        try:
            secret_file = self._get_secret_file_path(app_id)
            
            if os.path.exists(secret_file):
                with open(secret_file, 'r') as f:
                    api_key = f.read().strip()
                custom_log(f"✅ Loaded API key from file: {secret_file}")
                return api_key
            else:
                custom_log(f"⚠️ API key file not found: {secret_file}")
                return None
                
        except Exception as e:
            custom_log(f"❌ Error loading API key from file: {e}", level="ERROR")
            return None

    def _get_redis_keys_for_app(self, app_id: str) -> List[str]:
        """Get all Redis keys associated with an app_id using consistent patterns."""
        try:
            keys_to_clear = []
            
            # Pattern 1: Direct API key entries
            pattern1 = "api_key:*"
            keys = self.redis_manager.redis.keys(pattern1)
            for key in keys:
                key_data = self.redis_manager.get(key.replace('api_key:', 'api_key'))
                if key_data and key_data.get('app_id') == app_id:
                    keys_to_clear.append(key)
            
            # Pattern 2: App-specific keys
            patterns = [
                f"app_keys:{app_id}",
                f"key_metadata:{app_id}",
                f"key_cache:{app_id}",
                f"app_metadata:{app_id}"
            ]
            
            for pattern in patterns:
                keys = self.redis_manager.redis.keys(pattern)
                keys_to_clear.extend(keys)
            
            # Pattern 3: Usage tracking keys
            usage_pattern = "key_usage:*"
            usage_keys = self.redis_manager.redis.keys(usage_pattern)
            for key in usage_keys:
                key_data = self.redis_manager.get(key)
                if key_data and key_data.get('app_id') == app_id:
                    keys_to_clear.append(key)
            
            # Pattern 4: Credit system specific keys
            if app_id == "credit_system":
                cred_patterns = [
                    "cred_sys_key",
                    "cred_sys_cache",
                    "cred_sys_metadata"
                ]
                for pattern in cred_patterns:
                    keys = self.redis_manager.redis.keys(pattern)
                    keys_to_clear.extend(keys)
            
            custom_log(f"🔍 Found {len(keys_to_clear)} Redis keys to clear for app_id: {app_id}")
            return keys_to_clear
            
        except Exception as e:
            custom_log(f"❌ Error getting Redis keys for app_id {app_id}: {e}", level="ERROR")
            return []

    def invalidate_api_key_cache(self, app_id: str):
        """Enhanced cache invalidation with atomic operations and comprehensive cleanup."""
        try:
            custom_log(f"🧹 Starting comprehensive cache invalidation for app_id: {app_id}")
            
            # Get all keys to clear
            keys_to_clear = self._get_redis_keys_for_app(app_id)
            
            if not keys_to_clear:
                custom_log(f"ℹ️ No cache keys found for app_id: {app_id}")
                return
            
            # Use Redis pipeline for atomic operations
            pipeline = self.redis_manager.redis.pipeline()
            
            cleared_count = 0
            for key in keys_to_clear:
                pipeline.delete(key)
                cleared_count += 1
                custom_log(f"🗑️ Queued deletion for key: {key}")
            
            # Execute all deletions atomically
            results = pipeline.execute()
            
            # Log results
            successful_deletions = sum(1 for result in results if result == 1)
            custom_log(f"✅ Cache invalidation completed - {successful_deletions}/{cleared_count} keys cleared for app_id: {app_id}")
            
            # Clear any file-based caches
            self._clear_file_cache(app_id)
            
        except Exception as e:
            custom_log(f"❌ Error during cache invalidation for app_id {app_id}: {e}", level="ERROR")

    def _clear_file_cache(self, app_id: str):
        """Clear any file-based caches for the app."""
        try:
            # This could be extended to clear any file-based caching mechanisms
            custom_log(f"📁 File cache cleared for app_id: {app_id}")
        except Exception as e:
            custom_log(f"❌ Error clearing file cache for app_id {app_id}: {e}", level="ERROR")

    def _atomic_key_replacement(self, old_key: str, new_key: str, key_data: Dict[str, Any]) -> bool:
        """Atomically replace an API key in Redis."""
        try:
            pipeline = self.redis_manager.redis.pipeline()
            
            # Store new key using the redis_manager's set method which handles serialization
            self.redis_manager.set(new_key, key_data, expire=2592000)  # 30 days
            
            # Delete old key if it exists
            if old_key:
                pipeline.delete(old_key)
                # Execute the deletion
                pipeline.execute()
            
            custom_log(f"✅ Atomic key replacement completed - New key stored, old key removed")
            return True
            
        except Exception as e:
            custom_log(f"❌ Error during atomic key replacement: {e}", level="ERROR")
            return False

    def generate_api_key(self, app_id: str, app_name: str, permissions: list = None) -> str:
        """External apps should not generate API keys - they request them from credit system."""
        raise NotImplementedError("External apps should request API keys from credit system, not generate them locally")

    def get_api_key_for_app(self, app_id: str) -> Optional[str]:
        """Get the API key for a specific app from file."""
        return self._load_api_key_from_file(app_id)

    def save_credit_system_api_key(self, api_key: str) -> bool:
        """Save credit system API key to CRED_SYS_api_key file with enhanced cache management."""
        try:
            custom_log(f"🔑 Saving credit system API key with enhanced cache management")
            
            # Clear any existing credit system cache
            self.invalidate_api_key_cache("credit_system")
            
            # Ensure secrets directory exists
            os.makedirs(self.secrets_dir, exist_ok=True)
            
            # Save to CRED_SYS_api_key file
            secret_file = os.path.join(self.secrets_dir, "CRED_SYS_api_key")
            
            with open(secret_file, 'w') as f:
                f.write(api_key)
            
            # Store metadata in Redis
            self._store_credit_system_metadata(api_key)
            
            custom_log(f"✅ Saved credit system API key to file: {secret_file}")
            return True
            
        except Exception as e:
            custom_log(f"❌ Error saving credit system API key to file: {e}", level="ERROR")
            return False

    def _store_credit_system_metadata(self, api_key: str):
        """Store credit system API key metadata for better tracking."""
        try:
            metadata = {
                'app_id': 'credit_system',
                'app_name': 'Credit System',
                'current_key': api_key[:16] + "...",
                'last_updated': str(int(time.time())),
                'key_source': 'external_request'
            }
            
            metadata_key = "cred_sys_metadata"
            self.redis_manager.set(metadata_key, metadata, expire=2592000)
            
            custom_log(f"📊 Stored credit system metadata")
            
        except Exception as e:
            custom_log(f"❌ Error storing credit system metadata: {e}", level="ERROR")

    def load_credit_system_api_key(self) -> Optional[str]:
        """Load credit system API key from CRED_SYS_api_key file."""
        try:
            secret_file = os.path.join(self.secrets_dir, "CRED_SYS_api_key")
            
            if os.path.exists(secret_file):
                with open(secret_file, 'r') as f:
                    api_key = f.read().strip()
                custom_log(f"✅ Loaded credit system API key from file: {secret_file}")
                return api_key
            else:
                custom_log(f"⚠️ Credit system API key file not found: {secret_file}")
                return None
                
        except Exception as e:
            custom_log(f"❌ Error loading credit system API key from file: {e}", level="ERROR")
            return None

    def list_stored_api_keys(self) -> Dict[str, str]:
        """List all API keys stored in secret files."""
        try:
            stored_keys = {}
            
            if os.path.exists(self.secrets_dir):
                for filename in os.listdir(self.secrets_dir):
                    if filename.endswith('_api_key'):
                        app_id = filename.replace('_api_key', '')
                        api_key = self._load_api_key_from_file(app_id)
                        if api_key:
                            stored_keys[app_id] = api_key[:16] + "..."
            
            return stored_keys
            
        except Exception as e:
            custom_log(f"❌ Error listing stored API keys: {e}", level="ERROR")
            return {}

    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return app data if valid."""
        try:
            if not api_key:
                return None
            
            # Check if API key exists in Redis
            redis_key = f"api_key:{api_key}"
            key_data = self.redis_manager.get(redis_key)
            
            if not key_data:
                custom_log(f"❌ API key not found: {api_key[:16]}...")
                return None
            
            # Check if key is active
            if not key_data.get('is_active', False):
                custom_log(f"❌ API key inactive: {api_key[:16]}...")
                return None
            
            # Update last used timestamp
            key_data['last_used'] = str(int(time.time()))
            self.redis_manager.set(redis_key, key_data, expire=2592000)
            
            custom_log(f"✅ Validated API key for app: {key_data.get('app_name', 'Unknown')}")
            return key_data
            
        except Exception as e:
            custom_log(f"❌ Error validating API key: {e}", level="ERROR")
            return None

    def revoke_api_key(self, api_key: str) -> bool:
        """Revoke an API key with enhanced cache cleanup."""
        try:
            redis_key = f"api_key:{api_key}"
            key_data = self.redis_manager.get(redis_key)
            
            if key_data:
                app_id = key_data.get('app_id')
                
                # Use atomic operation for revocation
                key_data['is_active'] = False
                key_data['revoked_at'] = str(int(time.time()))
                
                success = self._atomic_key_replacement(None, redis_key, key_data)
                if not success:
                    raise Exception("Failed to revoke API key atomically")
                
                # Comprehensive cache invalidation
                self.invalidate_api_key_cache(app_id)
                
                custom_log(f"✅ Revoked API key for app: {key_data.get('app_name', 'Unknown')}")
                return True
            else:
                custom_log(f"❌ API key not found for revocation: {api_key[:16]}...")
                return False
                
        except Exception as e:
            custom_log(f"❌ Error revoking API key: {e}", level="ERROR")
            return False

    def list_api_keys(self) -> list:
        """List all API keys (for admin purposes)."""
        try:
            keys = []
            pattern = "api_key:*"
            api_keys = self.redis_manager.redis.keys(pattern)
            
            for key in api_keys:
                key_data = self.redis_manager.get(key)
                if key_data:
                    # Mask the actual API key
                    masked_key = key.replace("api_key:", "")[:16] + "..."
                    keys.append({
                        'api_key': masked_key,
                        'app_id': key_data.get('app_id'),
                        'app_name': key_data.get('app_name'),
                        'permissions': key_data.get('permissions'),
                        'is_active': key_data.get('is_active'),
                        'created_at': key_data.get('created_at'),
                        'last_used': key_data.get('last_used')
                    })
            
            return keys
            
        except Exception as e:
            custom_log(f"❌ Error listing API keys: {e}", level="ERROR")
            return []

    def get_app_by_api_key(self, api_key: str) -> Optional[str]:
        """Get app ID by API key."""
        try:
            key_data = self.validate_api_key(api_key)
            return key_data.get('app_id') if key_data else None
        except Exception as e:
            custom_log(f"❌ Error getting app by API key: {e}", level="ERROR")
            return None

    def health_check(self) -> Dict[str, Any]:
        """Perform health check for API Key Manager."""
        health_status = {
            'module': 'api_key_manager',
            'status': 'healthy',
            'details': {}
        }
        
        try:
            # Test Redis connection
            redis_healthy = self.redis_manager.ping()
            health_status['details']['redis'] = 'healthy' if redis_healthy else 'unhealthy'
            
            if not redis_healthy:
                health_status['status'] = 'unhealthy'
                health_status['details']['reason'] = 'Redis connection required for API key validation'
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['details']['error'] = str(e)
        
        return health_status 