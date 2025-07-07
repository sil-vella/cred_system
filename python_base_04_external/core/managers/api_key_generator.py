import requests
import time
import os
from typing import Optional
from tools.logger.custom_logging import custom_log
from utils.config.config import Config


class APIKeyGenerator:
    def __init__(self):
        """Initialize the API Key Generator."""
        self.credit_system_url = Config.CREDIT_SYSTEM_URL
        self.app_id = "external_app_001"
        self.app_name = "External Application"
        self.secret_file_path = "/app/secrets/credit_system_api_key"
        custom_log("APIKeyGenerator initialized")

    def generate_app_api_key(self) -> Optional[str]:
        """Generate API key from credit system if not already exists."""
        try:
            # Check if we already have an API key
            if Config.CREDIT_SYSTEM_API_KEY and Config.CREDIT_SYSTEM_API_KEY != "":
                custom_log("✅ API key already exists, skipping generation")
                return Config.CREDIT_SYSTEM_API_KEY
            
            custom_log("🔄 No API key found, generating from credit system...")
            
            # Prepare request to credit system
            payload = {
                "app_id": self.app_id,
                "app_name": self.app_name,
                "permissions": ["read", "write"]
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Make request to credit system
            response = requests.post(
                f"{self.credit_system_url}/api-keys/generate",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            # Accept both 200 and 201 as success if api_key is present
            if response.status_code in (200, 201):
                response_data = response.json()
                if response_data.get('success') and response_data.get('api_key'):
                    api_key = response_data['api_key']
                    custom_log(f"✅ Successfully generated API key: {api_key[:16]}...")
                    # Save to secret file for persistence
                    self.save_api_key_to_file(api_key)
                    return api_key
                else:
                    custom_log(f"❌ Credit system response missing API key: {response_data}")
                    return None
            else:
                custom_log(f"❌ Failed to generate API key. Status: {response.status_code}, Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            custom_log(f"❌ Network error generating API key: {e}")
            return None
        except Exception as e:
            custom_log(f"❌ Unexpected error generating API key: {e}")
            return None

    def save_api_key_to_file(self, api_key: str) -> bool:
        """Save API key to secret file for persistence."""
        try:
            # Use the API key manager to save the credit system API key
            from core.managers.api_key_manager import APIKeyManager
            api_key_manager = APIKeyManager()
            return api_key_manager.save_credit_system_api_key(api_key)
            
        except Exception as e:
            custom_log(f"❌ Error saving API key to file: {e}")
            return False

    def load_api_key_from_file(self) -> Optional[str]:
        """Load API key from secret file."""
        try:
            # Use the API key manager to load the credit system API key
            from core.managers.api_key_manager import APIKeyManager
            api_key_manager = APIKeyManager()
            return api_key_manager.load_credit_system_api_key()
            
        except Exception as e:
            custom_log(f"❌ Error loading API key from file: {e}")
            return None

    def validate_existing_api_key(self, api_key: str) -> bool:
        """Validate an existing API key with the credit system."""
        try:
            payload = {"api_key": api_key}
            headers = {"Content-Type": "application/json"}
            
            response = requests.post(
                f"{self.credit_system_url}/api-keys/validate",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                response_data = response.json()
                return response_data.get('valid', False)
            else:
                custom_log(f"❌ Failed to validate API key. Status: {response.status_code}")
                return False
                
        except Exception as e:
            custom_log(f"❌ Error validating API key: {e}")
            return False

    def health_check(self) -> dict:
        """Perform health check for API Key Generator."""
        try:
            # Test connection to credit system
            response = requests.get(
                f"{self.credit_system_url}/health",
                timeout=5
            )
            
            credit_system_status = "healthy" if response.status_code == 200 else "unhealthy"
            
            # Check if secret file exists
            secret_file_exists = os.path.exists(self.secret_file_path)
            
            return {
                "module": "api_key_generator",
                "status": "healthy" if credit_system_status == "healthy" else "unhealthy",
                "details": {
                    "credit_system_connection": credit_system_status,
                    "credit_system_url": self.credit_system_url,
                    "api_key_configured": bool(Config.CREDIT_SYSTEM_API_KEY),
                    "secret_file_exists": secret_file_exists,
                    "secret_file_path": self.secret_file_path
                }
            }
            
        except Exception as e:
            return {
                "module": "api_key_generator",
                "status": "unhealthy",
                "details": {
                    "error": str(e),
                    "credit_system_url": self.credit_system_url
                }
            } 