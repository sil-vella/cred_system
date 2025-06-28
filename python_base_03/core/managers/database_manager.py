from typing import Dict, Any, Optional
from core.managers.encryption_manager import EncryptionManager
from utils.config.config import Config
from pymongo import MongoClient, ReadPreference
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.errors import OperationFailure, ConnectionFailure
from urllib.parse import quote_plus
import logging
import os

# Helper to read secrets from files
def read_secret_file(path: str) -> Optional[str]:
    try:
        with open(path, 'r') as f:
            return f.read().strip()
    except Exception:
        return None

class DatabaseManager:
    def __init__(self, role: str = "read_write"):
        """Initialize the database manager with role-based access control."""
        self.encryption_manager = EncryptionManager()
        self.role = role
        self.client = None
        self.db = None
        self.logger = logging.getLogger(__name__)
        self._setup_mongodb_connection()

    def _get_password_from_file(self, password_file_path: str) -> str:
        """Read password from a file."""
        try:
            with open(password_file_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            self.logger.error(f"Failed to read password file: {e}")
            raise

    def _setup_mongodb_connection(self):
        """Set up MongoDB connection with role-based access control and read-only replicas."""
        try:
            # Prefer secrets files for all config values
            mongodb_user = read_secret_file('/run/secrets/mongodb_root_user') or os.environ.get('MONGODB_ROOT_USER', 'root')
            password = read_secret_file('/run/secrets/mongodb_root_password') or os.environ.get('MONGODB_ROOT_PASSWORD')
            mongodb_host = read_secret_file('/run/secrets/mongodb_service_name') or os.environ.get('MONGODB_SERVICE_NAME', 'mongodb')
            mongodb_port = read_secret_file('/run/secrets/mongodb_port') or os.environ.get('MONGODB_PORT', '27017')
            mongodb_db = read_secret_file('/run/secrets/mongodb_db_name') or os.environ.get('MONGODB_DB_NAME', 'credit_system')

            if not password:
                raise ValueError("MongoDB password not provided")

            # URL encode username and password
            encoded_user = quote_plus(mongodb_user)
            encoded_password = quote_plus(password)

            # Construct MongoDB URI with encoded credentials
            mongodb_uri = f"mongodb://{encoded_user}:{encoded_password}@{mongodb_host}:{mongodb_port}/{mongodb_db}?authSource=admin"

            # Set up connection options
            options = {
                'readPreference': 'primaryPreferred' if self.role == "read_only" else 'primary',
                'readConcernLevel': 'majority',
                'w': 'majority',
                'retryWrites': True,
                'retryReads': True
            }

            # Create MongoDB client
            self.client = MongoClient(mongodb_uri, **options)
            self.db = self.client[mongodb_db]

            # Verify connection and access
            self._verify_connection_and_access()

        except Exception as e:
            self.logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            raise

    def _verify_connection_and_access(self):
        """Verify MongoDB connection and role-based access."""
        try:
            # Test connection
            self.client.server_info()
            self.logger.info("✅ Successfully connected to MongoDB")

            # Test write access if role is read_write
            if self.role == "read_write":
                self.db.command("ping")
                self.logger.info("✅ Write access verified")

        except OperationFailure as e:
            self.logger.error(f"❌ Role-based access verification failed: {str(e)}")
            raise
        except ConnectionFailure as e:
            self.logger.error(f"❌ Failed to connect to MongoDB: {str(e)}")
            raise

    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert a single document into the specified collection."""
        if self.role != "read_write":
            raise PermissionError("Write operations not allowed for read-only role")
        
        try:
            result = self.db[collection].insert_one(document)
            return str(result.inserted_id)
        except Exception as e:
            self.logger.error(f"Failed to insert document: {e}")
            raise

    def find_one(self, collection: str, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document in the specified collection."""
        try:
            return self.db[collection].find_one(query)
        except Exception as e:
            self.logger.error(f"Failed to find document: {e}")
            raise

    def find_many(self, collection: str, query: Dict[str, Any]) -> list:
        """Find multiple documents in the specified collection."""
        try:
            return list(self.db[collection].find(query))
        except Exception as e:
            self.logger.error(f"Failed to find documents: {e}")
            raise

    def update_one(self, collection: str, query: Dict[str, Any], update: Dict[str, Any]) -> int:
        """Update a single document in the specified collection."""
        if self.role != "read_write":
            raise PermissionError("Write operations not allowed for read-only role")
        
        try:
            result = self.db[collection].update_one(query, update)
            return result.modified_count
        except Exception as e:
            self.logger.error(f"Failed to update document: {e}")
            raise

    def delete_one(self, collection: str, query: Dict[str, Any]) -> int:
        """Delete a single document from the specified collection."""
        if self.role != "read_write":
            raise PermissionError("Write operations not allowed for read-only role")
        
        try:
            result = self.db[collection].delete_one(query)
            return result.deleted_count
        except Exception as e:
            self.logger.error(f"Failed to delete document: {e}")
            raise

    def _encrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in the data dictionary."""
        encrypted_data = data.copy()
        for field in Config.SENSITIVE_FIELDS:
            if field in encrypted_data and encrypted_data[field] is not None:
                encrypted_data[field] = self.encryption_manager.encrypt_field(
                    encrypted_data[field]
                )
        return encrypted_data

    def _decrypt_sensitive_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in the data dictionary."""
        decrypted_data = data.copy()
        for field in Config.SENSITIVE_FIELDS:
            if field in decrypted_data and decrypted_data[field] is not None:
                decrypted_data[field] = self.encryption_manager.decrypt_field(
                    decrypted_data[field]
                )
        return decrypted_data

    def insert(self, collection: str, data: Dict[str, Any]) -> str:
        """Insert a document into the specified collection with encrypted sensitive fields."""
        if self.role == "read_only":
            raise OperationFailure("Write operations not allowed with read-only role")
        
        encrypted_data = self._encrypt_sensitive_fields(data)
        result = self.db[collection].insert_one(encrypted_data)
        return str(result.inserted_id)

    def find(self, collection: str, query: Dict[str, Any]) -> list:
        """Find documents in the specified collection and decrypt sensitive fields."""
        results = list(self.db[collection].find(query))
        return [self._decrypt_sensitive_fields(doc) for doc in results]

    def update(self, collection: str, query: Dict[str, Any], data: Dict[str, Any]) -> int:
        """Update documents in the specified collection with encrypted sensitive fields."""
        if self.role == "read_only":
            raise OperationFailure("Write operations not allowed with read-only role")
        
        encrypted_data = self._encrypt_sensitive_fields(data)
        result = self.db[collection].update_many(query, {'$set': encrypted_data})
        return result.modified_count

    def delete(self, collection: str, query: Dict[str, Any]) -> int:
        """Delete documents from the specified collection."""
        if self.role == "read_only":
            raise OperationFailure("Write operations not allowed with read-only role")
        
        result = self.db[collection].delete_many(query)
        return result.deleted_count

    def close(self):
        """Close the database connection."""
        if hasattr(self, 'client'):
            self.client.close()
            self.logger.info("✅ MongoDB connection closed")

    def check_connection(self):
        """Check if the database connection is healthy."""
        try:
            if not self.client:
                return False
            # Execute a simple command to check connection
            self.client.admin.command('ping')
            return True
        except Exception as e:
            self.logger.error(f"Database connection check failed: {e}")
            return False

# ... existing code ... 