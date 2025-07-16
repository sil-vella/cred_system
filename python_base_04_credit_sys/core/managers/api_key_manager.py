import hashlib
import hmac
import time
import os
from typing import Dict, Any, Optional, List
from tools.logger.custom_logging import custom_log
from utils.config.config import Config
from core.managers.redis_manager import RedisManager
from flask import request, jsonify


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
            'app_metadata': 'app_metadata:{app_id}'
        }
        custom_log("APIKeyManager initialized with robust cache cleanup")

    def _get_secret_file_path(self, app_id: str, app_name: str = None) -> str:
        """Get the secret file path for an app."""
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
        """Generate a new API key for an external app with enhanced cache management."""
        try:
            custom_log(f"🔑 Starting API key generation for app: {app_name} ({app_id})")
            
            # Comprehensive cache invalidation before generation
            self.invalidate_api_key_cache(app_id)
            
            # Create a unique API key
            timestamp = str(int(time.time()))
            unique_id = f"{app_id}_{timestamp}"
            
            # Generate API key using HMAC
            api_key = hmac.new(
                self.secret_key.encode(),
                unique_id.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Store API key metadata in Redis
            key_data = {
                'app_id': app_id,
                'app_name': app_name,
                'permissions': permissions or ['read', 'write'],
                'created_at': timestamp,
                'is_active': True,
                'last_used': None,
                'version': '1.0'  # Add version for future compatibility
            }
            
            # Store in Redis with expiration (30 days)
            redis_key = f"api_key:{api_key}"
            
            # Use atomic operation for storing
            success = self._atomic_key_replacement(None, redis_key, key_data)
            if not success:
                raise Exception("Failed to store API key atomically")
            
            # Save API key to secret file
            self._save_api_key_to_file(app_id, api_key, key_data)
            
            # Store additional metadata
            self._store_app_metadata(app_id, app_name, api_key)
            
            custom_log(f"✅ Generated API key for app: {app_name} ({app_id}) - Key: {api_key[:16]}...")
            return api_key
            
        except Exception as e:
            custom_log(f"❌ Error generating API key: {e}", level="ERROR")
            raise

    def _store_app_metadata(self, app_id: str, app_name: str, api_key: str):
        """Store additional app metadata for better tracking."""
        try:
            metadata = {
                'app_id': app_id,
                'app_name': app_name,
                'current_key': api_key[:16] + "...",
                'last_updated': str(int(time.time())),
                'key_count': 1
            }
            
            metadata_key = f"app_metadata:{app_id}"
            self.redis_manager.set(metadata_key, metadata, expire=2592000)
            
            custom_log(f"📊 Stored app metadata for: {app_name}")
            
        except Exception as e:
            custom_log(f"❌ Error storing app metadata: {e}", level="ERROR")

    def get_api_key_for_app(self, app_id: str) -> Optional[str]:
        """Get the API key for a specific app from file with enhanced logging."""
        custom_log(f"🔍 Searching for API key for app_id: {app_id}")
        
        # Try to find the API key file by scanning all files and matching app_id
        try:
            if os.path.exists(self.secrets_dir):
                custom_log(f"📁 Scanning secrets directory: {self.secrets_dir}")
                api_key_files = []
                
                for filename in os.listdir(self.secrets_dir):
                    if filename.endswith('_api_key'):
                        api_key_files.append(filename)
                        custom_log(f"📄 Found API key file: {filename}")
                
                custom_log(f"📊 Total API key files found: {len(api_key_files)}")
                
                for filename in api_key_files:
                    secret_file = os.path.join(self.secrets_dir, filename)
                    custom_log(f"🔍 Checking file: {secret_file}")
                    
                    try:
                        with open(secret_file, 'r') as f:
                            api_key = f.read().strip()
                        
                        if not api_key:
                            custom_log(f"⚠️ Empty API key in file: {secret_file}")
                            continue
                        
                        custom_log(f"🔑 Found API key in file: {api_key[:16]}...")
                        
                        # Check if this API key is for the requested app_id
                        redis_key = f"api_key:{api_key}"
                        custom_log(f"🔍 Checking Redis for key: {redis_key}")
                        
                        key_data = self.redis_manager.get(redis_key)
                        if key_data:
                            custom_log(f"✅ Found key data in Redis: {key_data.get('app_id', 'Unknown')}")
                            if key_data.get('app_id') == app_id:
                                custom_log(f"✅ MATCH FOUND! API key for app_id '{app_id}' found in file: {secret_file}")
                                custom_log(f"📋 Key details - App: {key_data.get('app_name', 'Unknown')}, Active: {key_data.get('is_active', False)}")
                                return api_key
                            else:
                                custom_log(f"❌ App ID mismatch - Expected: {app_id}, Found: {key_data.get('app_id', 'Unknown')}")
                        else:
                            custom_log(f"⚠️ No Redis data found for API key: {api_key[:16]}...")
                            
                    except Exception as e:
                        custom_log(f"❌ Error reading file {secret_file}: {e}", level="ERROR")
                        continue
                
                custom_log(f"❌ No matching API key found for app_id: {app_id}")
                return None
            else:
                custom_log(f"❌ Secrets directory does not exist: {self.secrets_dir}")
                return None
            
        except Exception as e:
            custom_log(f"❌ Error getting API key for app {app_id}: {e}", level="ERROR")
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

    # HTTP Endpoint Methods
    def generate_api_key_endpoint(self):
        """HTTP endpoint for API key generation."""
        try:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['app_id', 'app_name']
            for field in required_fields:
                if not data.get(field):
                    return jsonify({
                        'success': False,
                        'error': f'Missing required field: {field}'
                    }), 400
            
            app_id = data['app_id']
            app_name = data['app_name']
            permissions = data.get('permissions', ['read', 'write'])
            
            # Check if API key already exists for this app
            existing_api_key = self.get_api_key_for_app(app_id)
            if existing_api_key:
                custom_log(f"✅ API key already exists for app: {app_name} ({app_id})")
                return jsonify({
                    'success': True,
                    'api_key': existing_api_key,
                    'app_id': app_id,
                    'app_name': app_name,
                    'permissions': permissions,
                    'message': 'API key already exists'
                }), 200
            
            # Generate new API key
            api_key = self.generate_api_key(app_id, app_name, permissions)
            
            return jsonify({
                'success': True,
                'api_key': api_key,
                'app_id': app_id,
                'app_name': app_name,
                'permissions': permissions
            }), 201
            
        except Exception as e:
            custom_log(f"❌ Error generating API key: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to generate API key: {str(e)}'
            }), 500

    def validate_api_key_endpoint(self):
        """HTTP endpoint for API key validation."""
        try:
            data = request.get_json()
            
            if not data.get('api_key'):
                return jsonify({
                    'success': False,
                    'error': 'API key required'
                }), 400
            
            api_key = data['api_key']
            key_data = self.validate_api_key(api_key)
            
            if key_data:
                return jsonify({
                    'success': True,
                    'valid': True,
                    'app_id': key_data.get('app_id'),
                    'app_name': key_data.get('app_name'),
                    'permissions': key_data.get('permissions'),
                    'is_active': key_data.get('is_active')
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'valid': False,
                    'error': 'Invalid or expired API key'
                }), 200
            
        except Exception as e:
            custom_log(f"❌ Error validating API key: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to validate API key: {str(e)}'
            }), 500

    def revoke_api_key_endpoint(self):
        """HTTP endpoint for API key revocation."""
        try:
            data = request.get_json()
            
            if not data.get('api_key'):
                return jsonify({
                    'success': False,
                    'error': 'API key required'
                }), 400
            
            api_key = data['api_key']
            success = self.revoke_api_key(api_key)
            
            if success:
                return jsonify({
                    'success': True,
                    'message': 'API key revoked successfully'
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Failed to revoke API key'
                }), 400
            
        except Exception as e:
            custom_log(f"❌ Error revoking API key: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to revoke API key: {str(e)}'
            }), 500

    def list_api_keys_endpoint(self):
        """HTTP endpoint for listing all API keys (admin only)."""
        try:
            keys = self.list_api_keys()
            
            return jsonify({
                'success': True,
                'api_keys': keys,
                'count': len(keys)
            }), 200
            
        except Exception as e:
            custom_log(f"❌ Error listing API keys: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to list API keys: {str(e)}'
            }), 500

    def list_stored_api_keys_endpoint(self):
        """HTTP endpoint for listing all API keys stored in secret files."""
        try:
            stored_keys = self.list_stored_api_keys()
            
            return jsonify({
                'success': True,
                'stored_api_keys': stored_keys,
                'count': len(stored_keys)
            }), 200
            
        except Exception as e:
            custom_log(f"❌ Error listing stored API keys: {e}", level="ERROR")
            return jsonify({
                'success': False,
                'error': f'Failed to list stored API keys: {str(e)}'
            }), 500

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