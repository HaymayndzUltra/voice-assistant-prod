"""
WP-10 Encryption & Secrets Management
Advanced encryption, key management, and secrets protection for AI system security
"""

import asyncio
import os
import base64
import secrets
import hashlib
from typing import Dict, Any, Optional, List, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import logging

# Cryptography imports
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class EncryptionAlgorithm(Enum):
    """Supported encryption algorithms"""
    AES_256_GCM = "aes_256_gcm"
    AES_256_CBC = "aes_256_cbc"
    CHACHA20_POLY1305 = "chacha20_poly1305"
    RSA_OAEP = "rsa_oaep"
    FERNET = "fernet"

class KeyType(Enum):
    """Types of encryption keys"""
    SYMMETRIC = "symmetric"
    ASYMMETRIC = "asymmetric"
    DERIVED = "derived"
    SECRET = "secret"

@dataclass
class EncryptionKey:
    """Encryption key metadata"""
    key_id: str
    key_type: KeyType
    algorithm: EncryptionAlgorithm
    created_at: float = field(default_factory=lambda: __import__('time').time())
    expires_at: Optional[float] = None
    purpose: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if key is expired"""
        if self.expires_at is None:
            return False
        return __import__('time').time() > self.expires_at

@dataclass
class EncryptedData:
    """Encrypted data container"""
    ciphertext: bytes
    algorithm: EncryptionAlgorithm
    key_id: str
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode('utf-8'),
            "algorithm": self.algorithm.value,
            "key_id": self.key_id,
            "nonce": base64.b64encode(self.nonce).decode('utf-8') if self.nonce else None,
            "tag": base64.b64encode(self.tag).decode('utf-8') if self.tag else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptedData':
        """Create from dictionary"""
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            algorithm=EncryptionAlgorithm(data["algorithm"]),
            key_id=data["key_id"],
            nonce=base64.b64decode(data["nonce"]) if data.get("nonce") else None,
            tag=base64.b64decode(data["tag"]) if data.get("tag") else None,
            metadata=data.get("metadata", {})
        )

class KeyManager:
    """Manage encryption keys"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("keys")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._keys: Dict[str, bytes] = {}
        self._key_metadata: Dict[str, EncryptionKey] = {}
        
        # Master key for key encryption
        self._master_key = self._get_or_create_master_key()
        
        # Load existing keys
        self._load_keys()
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master key for key encryption"""
        master_key_file = self.storage_path / "master.key"
        
        if master_key_file.exists():
            with open(master_key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new master key
            master_key = secrets.token_bytes(32)
            
            # Save securely (in production, use HSM or key management service)
            with open(master_key_file, 'wb') as f:
                f.write(master_key)
            
            # Set restrictive permissions
            os.chmod(master_key_file, 0o600)
            
            return master_key
    
    def _load_keys(self):
        """Load keys from storage"""
        try:
            keys_file = self.storage_path / "keys.json"
            if keys_file.exists():
                with open(keys_file, 'r') as f:
                    data = json.load(f)
                
                # Load key metadata
                for key_id, metadata in data.get("metadata", {}).items():
                    self._key_metadata[key_id] = EncryptionKey(
                        key_id=metadata["key_id"],
                        key_type=KeyType(metadata["key_type"]),
                        algorithm=EncryptionAlgorithm(metadata["algorithm"]),
                        created_at=metadata["created_at"],
                        expires_at=metadata.get("expires_at"),
                        purpose=metadata.get("purpose", "general"),
                        metadata=metadata.get("metadata", {})
                    )
                
                # Load encrypted keys
                fernet = Fernet(base64.urlsafe_b64encode(self._master_key))
                for key_id, encrypted_key in data.get("keys", {}).items():
                    decrypted_key = fernet.decrypt(encrypted_key.encode('utf-8'))
                    self._keys[key_id] = decrypted_key
                    
        except Exception as e:
            logger.error(f"Error loading keys: {e}")
    
    def _save_keys(self):
        """Save keys to storage"""
        try:
            fernet = Fernet(base64.urlsafe_b64encode(self._master_key))
            
            # Encrypt keys
            encrypted_keys = {}
            for key_id, key_bytes in self._keys.items():
                encrypted_key = fernet.encrypt(key_bytes)
                encrypted_keys[key_id] = encrypted_key.decode('utf-8')
            
            # Prepare metadata
            metadata = {}
            for key_id, key_meta in self._key_metadata.items():
                metadata[key_id] = {
                    "key_id": key_meta.key_id,
                    "key_type": key_meta.key_type.value,
                    "algorithm": key_meta.algorithm.value,
                    "created_at": key_meta.created_at,
                    "expires_at": key_meta.expires_at,
                    "purpose": key_meta.purpose,
                    "metadata": key_meta.metadata
                }
            
            # Save to file
            keys_file = self.storage_path / "keys.json"
            with open(keys_file, 'w') as f:
                json.dump({
                    "keys": encrypted_keys,
                    "metadata": metadata
                }, f)
            
            # Set restrictive permissions
            os.chmod(keys_file, 0o600)
            
        except Exception as e:
            logger.error(f"Error saving keys: {e}")
    
    def generate_key(self, algorithm: EncryptionAlgorithm, 
                    purpose: str = "general",
                    expires_in: Optional[float] = None) -> str:
        """Generate new encryption key"""
        key_id = f"key_{secrets.token_urlsafe(16)}"
        
        # Generate key based on algorithm
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            key_bytes = secrets.token_bytes(32)  # 256 bits
            key_type = KeyType.SYMMETRIC
            
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            key_bytes = secrets.token_bytes(32)  # 256 bits
            key_type = KeyType.SYMMETRIC
            
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            key_bytes = secrets.token_bytes(32)  # 256 bits
            key_type = KeyType.SYMMETRIC
            
        elif algorithm == EncryptionAlgorithm.FERNET:
            key_bytes = Fernet.generate_key()
            key_type = KeyType.SYMMETRIC
            
        elif algorithm == EncryptionAlgorithm.RSA_OAEP:
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            
            # Serialize private key
            key_bytes = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            key_type = KeyType.ASYMMETRIC
            
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
        
        # Create key metadata
        expires_at = None
        if expires_in:
            expires_at = __import__('time').time() + expires_in
        
        key_metadata = EncryptionKey(
            key_id=key_id,
            key_type=key_type,
            algorithm=algorithm,
            expires_at=expires_at,
            purpose=purpose
        )
        
        # Store key and metadata
        self._keys[key_id] = key_bytes
        self._key_metadata[key_id] = key_metadata
        
        # Save to storage
        self._save_keys()
        
        logger.info(f"Generated {algorithm.value} key: {key_id}")
        return key_id
    
    def get_key(self, key_id: str) -> Optional[bytes]:
        """Get key by ID"""
        metadata = self._key_metadata.get(key_id)
        if metadata and metadata.is_expired():
            self.delete_key(key_id)
            return None
        
        return self._keys.get(key_id)
    
    def get_key_metadata(self, key_id: str) -> Optional[EncryptionKey]:
        """Get key metadata"""
        return self._key_metadata.get(key_id)
    
    def delete_key(self, key_id: str) -> bool:
        """Delete key"""
        if key_id in self._keys:
            del self._keys[key_id]
            del self._key_metadata[key_id]
            self._save_keys()
            logger.info(f"Deleted key: {key_id}")
            return True
        return False
    
    def list_keys(self, purpose: str = None) -> List[EncryptionKey]:
        """List available keys"""
        keys = []
        for metadata in self._key_metadata.values():
            if metadata.is_expired():
                continue
            if purpose and metadata.purpose != purpose:
                continue
            keys.append(metadata)
        return keys
    
    def rotate_key(self, old_key_id: str) -> str:
        """Rotate encryption key"""
        old_metadata = self._key_metadata.get(old_key_id)
        if not old_metadata:
            raise ValueError(f"Key not found: {old_key_id}")
        
        # Generate new key with same properties
        new_key_id = self.generate_key(
            old_metadata.algorithm,
            old_metadata.purpose,
            old_metadata.expires_at - __import__('time').time() if old_metadata.expires_at else None
        )
        
        logger.info(f"Rotated key {old_key_id} -> {new_key_id}")
        return new_key_id

class EncryptionService:
    """Encryption and decryption service"""
    
    def __init__(self, key_manager: KeyManager = None):
        self.key_manager = key_manager or KeyManager()
    
    def encrypt(self, data: Union[str, bytes], key_id: str) -> EncryptedData:
        """Encrypt data using specified key"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        key_bytes = self.key_manager.get_key(key_id)
        if not key_bytes:
            raise ValueError(f"Key not found: {key_id}")
        
        metadata = self.key_manager.get_key_metadata(key_id)
        algorithm = metadata.algorithm
        
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            return self._encrypt_aes_gcm(data, key_bytes, key_id)
        
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            return self._encrypt_aes_cbc(data, key_bytes, key_id)
        
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            return self._encrypt_chacha20(data, key_bytes, key_id)
        
        elif algorithm == EncryptionAlgorithm.FERNET:
            return self._encrypt_fernet(data, key_bytes, key_id)
        
        elif algorithm == EncryptionAlgorithm.RSA_OAEP:
            return self._encrypt_rsa(data, key_bytes, key_id)
        
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def decrypt(self, encrypted_data: EncryptedData) -> bytes:
        """Decrypt data"""
        key_bytes = self.key_manager.get_key(encrypted_data.key_id)
        if not key_bytes:
            raise ValueError(f"Key not found: {encrypted_data.key_id}")
        
        algorithm = encrypted_data.algorithm
        
        if algorithm == EncryptionAlgorithm.AES_256_GCM:
            return self._decrypt_aes_gcm(encrypted_data, key_bytes)
        
        elif algorithm == EncryptionAlgorithm.AES_256_CBC:
            return self._decrypt_aes_cbc(encrypted_data, key_bytes)
        
        elif algorithm == EncryptionAlgorithm.CHACHA20_POLY1305:
            return self._decrypt_chacha20(encrypted_data, key_bytes)
        
        elif algorithm == EncryptionAlgorithm.FERNET:
            return self._decrypt_fernet(encrypted_data, key_bytes)
        
        elif algorithm == EncryptionAlgorithm.RSA_OAEP:
            return self._decrypt_rsa(encrypted_data, key_bytes)
        
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")
    
    def _encrypt_aes_gcm(self, data: bytes, key: bytes, key_id: str) -> EncryptedData:
        """Encrypt using AES-256-GCM"""
        nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.AES_256_GCM,
            key_id=key_id,
            nonce=nonce,
            tag=encryptor.tag
        )
    
    def _decrypt_aes_gcm(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using AES-256-GCM"""
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(encrypted_data.nonce, encrypted_data.tag),
            backend=default_backend()
        )
        
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()
    
    def _encrypt_aes_cbc(self, data: bytes, key: bytes, key_id: str) -> EncryptedData:
        """Encrypt using AES-256-CBC"""
        # Pad data to block size
        block_size = 16
        padding_length = block_size - (len(data) % block_size)
        padded_data = data + bytes([padding_length] * padding_length)
        
        nonce = secrets.token_bytes(16)  # 128-bit IV for CBC
        
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(nonce),
            backend=default_backend()
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded_data) + encryptor.finalize()
        
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.AES_256_CBC,
            key_id=key_id,
            nonce=nonce
        )
    
    def _decrypt_aes_cbc(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using AES-256-CBC"""
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(encrypted_data.nonce),
            backend=default_backend()
        )
        
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()
        
        # Remove padding
        padding_length = padded_data[-1]
        return padded_data[:-padding_length]
    
    def _encrypt_chacha20(self, data: bytes, key: bytes, key_id: str) -> EncryptedData:
        """Encrypt using ChaCha20-Poly1305"""
        nonce = secrets.token_bytes(12)  # 96-bit nonce
        
        cipher = Cipher(
            algorithms.ChaCha20(key, nonce),
            mode=None,
            backend=default_backend()
        )
        
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.CHACHA20_POLY1305,
            key_id=key_id,
            nonce=nonce
        )
    
    def _decrypt_chacha20(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using ChaCha20-Poly1305"""
        cipher = Cipher(
            algorithms.ChaCha20(key, encrypted_data.nonce),
            mode=None,
            backend=default_backend()
        )
        
        decryptor = cipher.decryptor()
        return decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()
    
    def _encrypt_fernet(self, data: bytes, key: bytes, key_id: str) -> EncryptedData:
        """Encrypt using Fernet"""
        fernet = Fernet(key)
        ciphertext = fernet.encrypt(data)
        
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.FERNET,
            key_id=key_id
        )
    
    def _decrypt_fernet(self, encrypted_data: EncryptedData, key: bytes) -> bytes:
        """Decrypt using Fernet"""
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data.ciphertext)
    
    def _encrypt_rsa(self, data: bytes, private_key_bytes: bytes, key_id: str) -> EncryptedData:
        """Encrypt using RSA-OAEP (using public key from private key)"""
        private_key = serialization.load_pem_private_key(
            private_key_bytes,
            password=None,
            backend=default_backend()
        )
        
        public_key = private_key.public_key()
        
        ciphertext = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return EncryptedData(
            ciphertext=ciphertext,
            algorithm=EncryptionAlgorithm.RSA_OAEP,
            key_id=key_id
        )
    
    def _decrypt_rsa(self, encrypted_data: EncryptedData, private_key_bytes: bytes) -> bytes:
        """Decrypt using RSA-OAEP"""
        private_key = serialization.load_pem_private_key(
            private_key_bytes,
            password=None,
            backend=default_backend()
        )
        
        return private_key.decrypt(
            encrypted_data.ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )

class SecretsManager:
    """Manage application secrets"""
    
    def __init__(self, encryption_service: EncryptionService = None):
        self.encryption_service = encryption_service or EncryptionService()
        self.storage_path = Path("secrets")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Default key for secrets
        self._secrets_key_id = self._get_or_create_secrets_key()
        
        # In-memory cache
        self._secrets_cache: Dict[str, Any] = {}
        
        # Load secrets
        self._load_secrets()
    
    def _get_or_create_secrets_key(self) -> str:
        """Get or create key for secrets encryption"""
        # Check if secrets key exists
        for key_meta in self.encryption_service.key_manager.list_keys("secrets"):
            return key_meta.key_id
        
        # Create new secrets key
        return self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.FERNET,
            purpose="secrets"
        )
    
    def _load_secrets(self):
        """Load secrets from storage"""
        try:
            secrets_file = self.storage_path / "secrets.json"
            if secrets_file.exists():
                with open(secrets_file, 'r') as f:
                    encrypted_secrets = json.load(f)
                
                for secret_name, encrypted_data_dict in encrypted_secrets.items():
                    encrypted_data = EncryptedData.from_dict(encrypted_data_dict)
                    decrypted_value = self.encryption_service.decrypt(encrypted_data)
                    
                    # Parse JSON if possible
                    try:
                        self._secrets_cache[secret_name] = json.loads(decrypted_value.decode('utf-8'))
                    except json.JSONDecodeError:
                        self._secrets_cache[secret_name] = decrypted_value.decode('utf-8')
                        
        except Exception as e:
            logger.error(f"Error loading secrets: {e}")
    
    def _save_secrets(self):
        """Save secrets to storage"""
        try:
            encrypted_secrets = {}
            
            for secret_name, secret_value in self._secrets_cache.items():
                # Serialize value
                if isinstance(secret_value, (dict, list)):
                    serialized_value = json.dumps(secret_value)
                else:
                    serialized_value = str(secret_value)
                
                # Encrypt secret
                encrypted_data = self.encryption_service.encrypt(
                    serialized_value,
                    self._secrets_key_id
                )
                
                encrypted_secrets[secret_name] = encrypted_data.to_dict()
            
            # Save to file
            secrets_file = self.storage_path / "secrets.json"
            with open(secrets_file, 'w') as f:
                json.dump(encrypted_secrets, f)
            
            # Set restrictive permissions
            os.chmod(secrets_file, 0o600)
            
        except Exception as e:
            logger.error(f"Error saving secrets: {e}")
    
    def set_secret(self, name: str, value: Any):
        """Set secret value"""
        self._secrets_cache[name] = value
        self._save_secrets()
        logger.info(f"Secret '{name}' updated")
    
    def get_secret(self, name: str, default: Any = None) -> Any:
        """Get secret value"""
        return self._secrets_cache.get(name, default)
    
    def delete_secret(self, name: str) -> bool:
        """Delete secret"""
        if name in self._secrets_cache:
            del self._secrets_cache[name]
            self._save_secrets()
            logger.info(f"Secret '{name}' deleted")
            return True
        return False
    
    def list_secrets(self) -> List[str]:
        """List secret names"""
        return list(self._secrets_cache.keys())
    
    def rotate_secrets_key(self):
        """Rotate the secrets encryption key"""
        old_key_id = self._secrets_key_id
        
        # Generate new key
        new_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.FERNET,
            purpose="secrets"
        )
        
        # Re-encrypt all secrets with new key
        for secret_name, secret_value in self._secrets_cache.items():
            # Temporarily store value
            temp_value = secret_value
            
            # Update key ID
            self._secrets_key_id = new_key_id
            
            # Re-encrypt with new key (this happens in _save_secrets)
            pass
        
        # Save with new key
        self._save_secrets()
        
        # Delete old key
        self.encryption_service.key_manager.delete_key(old_key_id)
        
        logger.info(f"Rotated secrets key: {old_key_id} -> {new_key_id}")

# Global instances
_encryption_service: Optional[EncryptionService] = None
_secrets_manager: Optional[SecretsManager] = None

def get_encryption_service() -> EncryptionService:
    """Get global encryption service"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service

def get_secrets_manager() -> SecretsManager:
    """Get global secrets manager"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

# Convenience functions
def encrypt_data(data: Union[str, bytes], algorithm: EncryptionAlgorithm = EncryptionAlgorithm.FERNET) -> Tuple[str, EncryptedData]:
    """Encrypt data with new key"""
    encryption_service = get_encryption_service()
    
    # Generate key
    key_id = encryption_service.key_manager.generate_key(algorithm)
    
    # Encrypt data
    encrypted_data = encryption_service.encrypt(data, key_id)
    
    return key_id, encrypted_data

def decrypt_data(encrypted_data: EncryptedData) -> bytes:
    """Decrypt data"""
    encryption_service = get_encryption_service()
    return encryption_service.decrypt(encrypted_data)

def set_secret(name: str, value: Any):
    """Set application secret"""
    secrets_manager = get_secrets_manager()
    secrets_manager.set_secret(name, value)

def get_secret(name: str, default: Any = None) -> Any:
    """Get application secret"""
    secrets_manager = get_secrets_manager()
    return secrets_manager.get_secret(name, default)

# Secure data utilities
def generate_secure_hash(data: Union[str, bytes]) -> str:
    """Generate secure hash of data"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    
    return hashlib.sha256(data).hexdigest()

def generate_secure_token(length: int = 32) -> str:
    """Generate cryptographically secure token"""
    return secrets.token_urlsafe(length)

def secure_compare(a: str, b: str) -> bool:
    """Constant-time string comparison"""
    return secrets.compare_digest(a.encode('utf-8'), b.encode('utf-8')) 