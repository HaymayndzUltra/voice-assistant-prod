
from common.config_manager import get_service_ip, get_service_url, get_redis_url
# WP-10 Encryption Integration for translation_service
# Add data encryption and secrets management

from common.security.encryption import (
    get_encryption_service, get_secrets_manager, 
    EncryptionAlgorithm, encrypt_data, decrypt_data,
    set_secret, get_secret
)

class TranslationServiceEncryptionIntegration:
    """Encryption integration for translation_service"""
    
    def __init__(self):
        self.encryption_service = get_encryption_service()
        self.secrets_manager = get_secrets_manager()
        
        # Generate encryption keys for different purposes
        self.data_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.AES_256_GCM,
            purpose="translation_service_data"
        )
        
        self.file_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.FERNET,
            purpose="translation_service_files"
        )
        
        # Setup application secrets
        self._setup_secrets()
    
    def _setup_secrets(self):
        """Setup application secrets"""
        # Store configuration secrets
        set_secret("translation_service_db_connection", {
            "host": "localhost",
            "port": 5432,
            "database": "translation_service_db",
            "username": "app_user",
            "password": "secure_password_123"
        })
        
        set_secret("translation_service_api_config", {
            "external_api_key": "sk_live_abc123xyz789",
            "webhook_secret": "whsec_secret_key_456",
            "encryption_key": "enc_key_789"
        })
    
    async def encrypt_sensitive_data(self, data: dict) -> dict:
        """Encrypt sensitive fields in data"""
        
        # Fields that should be encrypted
        sensitive_fields = ['password', 'secret', 'key', 'token', 'credential']
        
        encrypted_data = data.copy()
        
        for field, value in data.items():
            if any(sensitive in field.lower() for sensitive in sensitive_fields):
                # Encrypt the field
                encrypted = self.encryption_service.encrypt(
                    str(value), 
                    self.data_key_id
                )
                
                # Store as encrypted data structure
                encrypted_data[field] = {
                    "encrypted": True,
                    "data": encrypted.to_dict()
                }
        
        return encrypted_data
    
    async def decrypt_sensitive_data(self, encrypted_data: dict) -> dict:
        """Decrypt sensitive fields in data"""
        
        decrypted_data = encrypted_data.copy()
        
        for field, value in encrypted_data.items():
            if isinstance(value, dict) and value.get("encrypted"):
                # Decrypt the field
                from common.security.encryption import EncryptedData
                encrypted = EncryptedData.from_dict(value["data"])
                
                decrypted_bytes = self.encryption_service.decrypt(encrypted)
                decrypted_data[field] = decrypted_bytes.decode('utf-8')
        
        return decrypted_data
    
    async def encrypt_file(self, file_path: str, output_path: str = None):
        """Encrypt file contents"""
        
        # Read file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Encrypt data
        encrypted = self.encryption_service.encrypt(file_data, self.file_key_id)
        
        # Write encrypted file
        output_file = output_path or f"{file_path}.encrypted"
        with open(output_file, 'w') as f:
            json.dump(encrypted.to_dict(), f)
        
        print(f"File encrypted: {file_path} -> {output_file}")
        return output_file
    
    async def decrypt_file(self, encrypted_file_path: str, output_path: str = None):
        """Decrypt file contents"""
        
        # Read encrypted file
        with open(encrypted_file_path, 'r') as f:
            encrypted_data_dict = json.load(f)
        
        # Decrypt data
        from common.security.encryption import EncryptedData
        encrypted = EncryptedData.from_dict(encrypted_data_dict)
        decrypted_data = self.encryption_service.decrypt(encrypted)
        
        # Write decrypted file
        output_file = output_path or encrypted_file_path.replace('.encrypted', '')
        with open(output_file, 'wb') as f:
            f.write(decrypted_data)
        
        print(f"File decrypted: {encrypted_file_path} -> {output_file}")
        return output_file
    
    def get_database_credentials(self) -> dict:
        """Get database credentials from secrets manager"""
        return get_secret("translation_service_db_connection")
    
    def get_api_configuration(self) -> dict:
        """Get API configuration from secrets manager"""
        return get_secret("translation_service_api_config")
    
    async def secure_data_storage(self, data_id: str, data: dict):
        """Store data with encryption"""
        
        # Encrypt sensitive data
        encrypted_data = await self.encrypt_sensitive_data(data)
        
        # Add metadata
        stored_data = {
            "data_id": data_id,
            "encrypted_at": time.time(),
            "encryption_key_id": self.data_key_id,
            "data": encrypted_data
        }
        
        # Store in database/file
        await self.store_data(data_id, stored_data)
        
        return data_id
    
    async def secure_data_retrieval(self, data_id: str) -> dict:
        """Retrieve and decrypt data"""
        
        # Retrieve from storage
        stored_data = await self.retrieve_data(data_id)
        
        if not stored_data:
            return None
        
        # Decrypt sensitive fields
        decrypted_data = await self.decrypt_sensitive_data(stored_data["data"])
        
        return decrypted_data
    
    def rotate_encryption_keys(self):
        """Rotate encryption keys"""
        
        old_data_key = self.data_key_id
        old_file_key = self.file_key_id
        
        # Generate new keys
        self.data_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.AES_256_GCM,
            purpose="translation_service_data"
        )
        
        self.file_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.FERNET,
            purpose="translation_service_files"
        )
        
        print(f"Rotated encryption keys:")
        print(f"  Data key: {old_data_key} -> {self.data_key_id}")
        print(f"  File key: {old_file_key} -> {self.file_key_id}")
        
        # Note: In production, you would need to re-encrypt existing data
        # with the new keys and then delete the old keys
    
    async def secure_communication(self, message: dict, recipient_public_key: str):
        """Encrypt message for secure communication"""
        
        # Generate temporary key for this message
        temp_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.AES_256_GCM,
            purpose="temp_communication"
        )
        
        # Encrypt message
        encrypted_message = self.encryption_service.encrypt(
            json.dumps(message),
            temp_key_id
        )
        
        # In real implementation, you would encrypt the temp_key_id
        # with the recipient's public key
        
        return {
            "encrypted_message": encrypted_message.to_dict(),
            "key_id": temp_key_id,
            "sender": "translation_service",
            "timestamp": time.time()
        }

# Example usage:
# encryption = TranslationServiceEncryptionIntegration()
# 
# # Encrypt sensitive data
# sensitive_data = {"username": "admin", "password": "secret123"}
# encrypted = await encryption.encrypt_sensitive_data(sensitive_data)
# 
# # Store securely
# await encryption.secure_data_storage("user_001", sensitive_data)
# 
# # Retrieve and decrypt
# decrypted = await encryption.secure_data_retrieval("user_001")
# 
# # Get secrets
# db_config = encryption.get_database_credentials()
# api_config = encryption.get_api_configuration()
