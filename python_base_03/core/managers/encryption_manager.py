from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
from typing import Any, Dict, Optional
from utils.config.config import Config

class EncryptionManager:
    """Manager for handling data encryption at rest."""
    
    # Encryption key derivation settings
    SALT_LENGTH = 16
    ITERATIONS = 100000
    
    def __init__(self):
        """Initialize the encryption manager."""
        self._fernet = None
        self._initialize_fernet()
    
    def _initialize_fernet(self) -> None:
        """Initialize the Fernet encryption instance."""
        # Use the centralized config system that handles files, environment, and Vault
        key = Config.ENCRYPTION_KEY
        
        if not key:
            raise RuntimeError("ENCRYPTION_KEY is required - check Vault, secret files, or environment variables")
        
        # Derive encryption key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=Config.ENCRYPTION_SALT.encode(),
            iterations=self.ITERATIONS
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
        
        # Initialize Fernet with derived key
        self._fernet = Fernet(derived_key)
    
    def encrypt_data(self, data: Any) -> str:
        """
        Encrypt data using AES-256.
        
        Args:
            data: Data to encrypt (will be converted to string)
            
        Returns:
            str: Encrypted data as base64 string
        """
        if not self._fernet:
            raise RuntimeError("Encryption manager not initialized")
        
        # Convert data to string if needed
        if not isinstance(data, str):
            data = str(data)
        
        # Encrypt data
        encrypted_data = self._fernet.encrypt(data.encode())
        return encrypted_data.decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt data that was encrypted using AES-256.
        
        Args:
            encrypted_data: Encrypted data as base64 string
            
        Returns:
            str: Decrypted data
        """
        if not self._fernet:
            raise RuntimeError("Encryption manager not initialized")
        
        # Decrypt data
        decrypted_data = self._fernet.decrypt(encrypted_data.encode())
        return decrypted_data.decode()
    
    def encrypt_sensitive_fields(self, data: Dict[str, Any], fields: list) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing data to encrypt
            fields: List of field names to encrypt
            
        Returns:
            Dict: Dictionary with encrypted fields
        """
        encrypted_data = data.copy()
        for field in fields:
            if field in encrypted_data and encrypted_data[field] is not None:
                encrypted_data[field] = self.encrypt_data(encrypted_data[field])
        return encrypted_data
    
    def decrypt_sensitive_fields(self, data: Dict[str, Any], fields: list) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
            
        Returns:
            Dict: Dictionary with decrypted fields
        """
        decrypted_data = data.copy()
        for field in fields:
            if field in decrypted_data and decrypted_data[field] is not None:
                decrypted_data[field] = self.decrypt_data(decrypted_data[field])
        return decrypted_data 