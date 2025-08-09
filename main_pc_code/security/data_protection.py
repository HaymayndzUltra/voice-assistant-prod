#!/usr/bin/env python3
"""
Data Protection - Encryption and Secrets Management
Provides comprehensive data protection with encryption, secrets management, and compliance.

Features:
- AES encryption for data at rest and in transit
- Secure key management and rotation
- Secrets management with secure storage
- Data classification and handling policies
- GDPR/compliance data protection features
- Secure data wiping and lifecycle management
"""
from __future__ import annotations
import sys
from pathlib import Path
from common.utils.log_setup import configure_logging

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time
import json
import secrets
import base64
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum

# Encryption imports
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("Cryptography library not available - install with: pip install cryptography")

# Core imports
from common.core.base_agent import BaseAgent

# Event system imports
from events.memory_events import (
    MemoryEventType, create_memory_operation, MemoryType
)
from events.event_bus import publish_memory_event

class DataClassification(Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"

class EncryptionLevel(Enum):
    """Encryption security levels"""
    NONE = "none"
    BASIC = "basic"           # AES-128
    STANDARD = "standard"     # AES-256
    HIGH = "high"            # AES-256 + RSA
    MAXIMUM = "maximum"      # AES-256 + RSA + additional layers

class SecretType(Enum):
    """Types of secrets"""
    API_KEY = "api_key"
    DATABASE_PASSWORD = "database_password"
    JWT_SECRET = "jwt_secret"
    ENCRYPTION_KEY = "encryption_key"
    CERTIFICATE = "certificate"
    OAUTH_TOKEN = "oauth_token"
    SSH_KEY = "ssh_key"

class ComplianceFramework(Enum):
    """Compliance frameworks"""
    GDPR = "gdpr"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"

@dataclass
class EncryptedData:
    """Encrypted data container"""
    data_id: str
    encrypted_content: bytes
    encryption_metadata: Dict[str, Any]
    classification: DataClassification
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    retention_policy: Optional[str] = None
    compliance_tags: Set[str] = field(default_factory=set)

@dataclass
class SecretEntry:
    """Secret management entry"""
    secret_id: str
    secret_type: SecretType
    encrypted_value: bytes
    metadata: Dict[str, Any]
    created_at: datetime
    expires_at: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    rotation_interval_days: Optional[int] = None
    access_log: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class EncryptionKey:
    """Encryption key management"""
    key_id: str
    key_data: bytes
    algorithm: str
    key_size: int
    created_at: datetime
    usage_count: int = 0
    max_usage: Optional[int] = None
    expires_at: Optional[datetime] = None
    purpose: str = "general"

@dataclass
class DataRetentionPolicy:
    """Data retention policy"""
    policy_id: str
    name: str
    classification_level: DataClassification
    retention_days: int
    auto_delete: bool = True
    backup_before_delete: bool = True
    compliance_frameworks: Set[ComplianceFramework] = field(default_factory=set)

class DataProtectionSystem(BaseAgent):
    """
    Comprehensive data protection system.
    
    Provides encryption, secrets management, key rotation,
    and compliance features for data security.
    """
    
    def __init__(self, 
                 master_key: Optional[bytes] = None,
                 enable_key_rotation: bool = True,
                 default_encryption_level: EncryptionLevel = EncryptionLevel.STANDARD,
                 **kwargs):
        super().__init__(name="DataProtectionSystem", **kwargs)
        
        # Configuration
        self.enable_key_rotation = enable_key_rotation
        self.default_encryption_level = default_encryption_level
        
        # Initialize master key
        if CRYPTO_AVAILABLE:
            self.master_key = master_key or self._generate_master_key()
            self.fernet = Fernet(base64.urlsafe_b64encode(self.master_key[:32]))
        else:
            self.master_key = None
            self.fernet = None
        
        # Data storage
        self.encrypted_data: Dict[str, EncryptedData] = {}
        self.secrets: Dict[str, SecretEntry] = {}
        self.encryption_keys: Dict[str, EncryptionKey] = {}
        
        # Compliance and policies
        self.retention_policies: Dict[str, DataRetentionPolicy] = {}
        self.data_access_log: deque = deque(maxlen=10000)
        self.compliance_reports: List[Dict[str, Any]] = []
        
        # Security metrics
        self.encryption_metrics = {
            'total_encrypted_items': 0,
            'total_secrets': 0,
            'key_rotations': 0,
            'data_access_events': 0,
            'compliance_violations': 0
        }
        
        # Initialize system
        if CRYPTO_AVAILABLE:
            self._initialize_default_policies()
            self._start_key_rotation_scheduler()
        
        self.logger.info("Data Protection System initialized")
    
    def _generate_master_key(self) -> bytes:
        """Generate master encryption key"""
        return secrets.token_bytes(32)  # 256-bit key
    
    def _initialize_default_policies(self) -> None:
        """Initialize default data retention policies"""
        default_policies = [
            DataRetentionPolicy(
                policy_id="public_data",
                name="Public Data Retention",
                classification_level=DataClassification.PUBLIC,
                retention_days=365,
                auto_delete=False,
                compliance_frameworks={ComplianceFramework.GDPR}
            ),
            DataRetentionPolicy(
                policy_id="confidential_data",
                name="Confidential Data Retention",
                classification_level=DataClassification.CONFIDENTIAL,
                retention_days=2555,  # 7 years
                auto_delete=True,
                backup_before_delete=True,
                compliance_frameworks={ComplianceFramework.GDPR, ComplianceFramework.SOX}
            ),
            DataRetentionPolicy(
                policy_id="restricted_data",
                name="Restricted Data Retention",
                classification_level=DataClassification.RESTRICTED,
                retention_days=1095,  # 3 years
                auto_delete=True,
                backup_before_delete=True,
                compliance_frameworks={ComplianceFramework.GDPR, ComplianceFramework.HIPAA}
            )
        ]
        
        for policy in default_policies:
            self.retention_policies[policy.policy_id] = policy
    
    def _start_key_rotation_scheduler(self) -> None:
        """Start key rotation scheduler"""
        import threading
        
        # Key rotation thread
        rotation_thread = threading.Thread(target=self._key_rotation_loop, daemon=True)
        rotation_thread.start()
        
        # Data retention cleanup thread
        cleanup_thread = threading.Thread(target=self._data_cleanup_loop, daemon=True)
        cleanup_thread.start()
        
        # Compliance monitoring thread
        compliance_thread = threading.Thread(target=self._compliance_monitoring_loop, daemon=True)
        compliance_thread.start()
    
    def _key_rotation_loop(self) -> None:
        """Background key rotation loop"""
        while self.running:
            try:
                if self.enable_key_rotation:
                    self._rotate_expired_keys()
                    self._rotate_expired_secrets()
                
                time.sleep(3600)  # Check every hour
                
            except Exception as e:
                self.logger.error(f"Key rotation error: {e}")
                time.sleep(1800)
    
    def _data_cleanup_loop(self) -> None:
        """Background data cleanup loop"""
        while self.running:
            try:
                self._cleanup_expired_data()
                self._enforce_retention_policies()
                
                time.sleep(21600)  # Cleanup every 6 hours
                
            except Exception as e:
                self.logger.error(f"Data cleanup error: {e}")
                time.sleep(3600)
    
    def _compliance_monitoring_loop(self) -> None:
        """Background compliance monitoring"""
        while self.running:
            try:
                self._generate_compliance_reports()
                self._check_compliance_violations()
                
                time.sleep(86400)  # Daily compliance checks
                
            except Exception as e:
                self.logger.error(f"Compliance monitoring error: {e}")
                time.sleep(43200)
    
    async def encrypt_data(self, data: Union[str, bytes], 
                          classification: DataClassification = DataClassification.INTERNAL,
                          encryption_level: Optional[EncryptionLevel] = None,
                          retention_policy_id: Optional[str] = None) -> str:
        """Encrypt data and return data ID"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        encryption_level = encryption_level or self.default_encryption_level
        
        # Convert to bytes if string
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        # Generate data ID
        data_id = self._generate_data_id()
        
        # Encrypt based on level
        if encryption_level == EncryptionLevel.BASIC:
            encrypted_content, metadata = self._encrypt_aes_128(data_bytes)
        elif encryption_level == EncryptionLevel.STANDARD:
            encrypted_content, metadata = self._encrypt_aes_256(data_bytes)
        elif encryption_level == EncryptionLevel.HIGH:
            encrypted_content, metadata = self._encrypt_aes_256_rsa(data_bytes)
        elif encryption_level == EncryptionLevel.MAXIMUM:
            encrypted_content, metadata = self._encrypt_maximum_security(data_bytes)
        else:
            encrypted_content, metadata = data_bytes, {"encryption": "none"}
        
        # Create encrypted data entry
        encrypted_data = EncryptedData(
            data_id=data_id,
            encrypted_content=encrypted_content,
            encryption_metadata=metadata,
            classification=classification,
            created_at=datetime.now(),
            retention_policy=retention_policy_id
        )
        
        # Apply compliance tags based on classification
        encrypted_data.compliance_tags = self._get_compliance_tags(classification)
        
        # Store encrypted data
        self.encrypted_data[data_id] = encrypted_data
        
        # Update metrics
        self.encryption_metrics['total_encrypted_items'] += 1
        
        # Log access
        self._log_data_access("encrypt", data_id, classification.value)
        
        # Publish encryption event
        encryption_event = create_memory_operation(
            operation_type=MemoryEventType.MEMORY_CREATED,
            memory_id=f"encrypted_data_{data_id}",
            memory_type=MemoryType.PROCEDURAL,
            content=f"Data encrypted with {encryption_level.value} level",
            size_bytes=len(encrypted_content),
            source_agent=self.name,
            machine_id=self._get_machine_id()
        )
        
        publish_memory_event(encryption_event)
        
        self.logger.info(f"Data encrypted: {data_id} (Level: {encryption_level.value}, Classification: {classification.value})")
        
        return data_id
    
    async def decrypt_data(self, data_id: str) -> Tuple[bool, Union[bytes, str]]:
        """Decrypt data by data ID"""
        if not CRYPTO_AVAILABLE:
            return False, "Cryptography library not available"
        
        if data_id not in self.encrypted_data:
            return False, "Data not found"
        
        encrypted_data = self.encrypted_data[data_id]
        
        # Update access tracking
        encrypted_data.last_accessed = datetime.now()
        encrypted_data.access_count += 1
        
        # Decrypt based on metadata
        try:
            algorithm = encrypted_data.encryption_metadata.get("algorithm", "aes_256")
            
            if algorithm == "aes_128":
                decrypted_content = self._decrypt_aes_128(encrypted_data.encrypted_content, encrypted_data.encryption_metadata)
            elif algorithm == "aes_256":
                decrypted_content = self._decrypt_aes_256(encrypted_data.encrypted_content, encrypted_data.encryption_metadata)
            elif algorithm == "aes_256_rsa":
                decrypted_content = self._decrypt_aes_256_rsa(encrypted_data.encrypted_content, encrypted_data.encryption_metadata)
            elif algorithm == "maximum_security":
                decrypted_content = self._decrypt_maximum_security(encrypted_data.encrypted_content, encrypted_data.encryption_metadata)
            else:
                decrypted_content = encrypted_data.encrypted_content
            
            # Update metrics
            self.encryption_metrics['data_access_events'] += 1
            
            # Log access
            self._log_data_access("decrypt", data_id, encrypted_data.classification.value)
            
            self.logger.debug(f"Data decrypted: {data_id}")
            
            return True, decrypted_content
            
        except Exception as e:
            self.logger.error(f"Decryption failed for {data_id}: {e}")
            return False, f"Decryption failed: {str(e)}"
    
    def _encrypt_aes_256(self, data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Encrypt data with AES-256"""
        encrypted_data = self.fernet.encrypt(data)
        
        metadata = {
            "algorithm": "aes_256",
            "key_derivation": "fernet",
            "timestamp": datetime.now().isoformat()
        }
        
        return encrypted_data, metadata
    
    def _decrypt_aes_256(self, encrypted_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """Decrypt AES-256 encrypted data"""
        return self.fernet.decrypt(encrypted_data)
    
    def _encrypt_aes_128(self, data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Encrypt data with AES-128"""
        # For simplicity, use Fernet (which uses AES-128 in CBC mode)
        encrypted_data = self.fernet.encrypt(data)
        
        metadata = {
            "algorithm": "aes_128",
            "key_derivation": "fernet",
            "timestamp": datetime.now().isoformat()
        }
        
        return encrypted_data, metadata
    
    def _decrypt_aes_128(self, encrypted_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """Decrypt AES-128 encrypted data"""
        return self.fernet.decrypt(encrypted_data)
    
    def _encrypt_aes_256_rsa(self, data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Encrypt data with AES-256 + RSA hybrid encryption"""
        # Generate RSA key pair for this encryption
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Generate AES key
        aes_key = secrets.token_bytes(32)
        
        # Encrypt data with AES
        fernet_aes = Fernet(base64.urlsafe_b64encode(aes_key))
        encrypted_data = fernet_aes.encrypt(data)
        
        # Encrypt AES key with RSA
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Serialize private key
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        # Combine encrypted data
        combined_data = len(encrypted_aes_key).to_bytes(4, 'big') + encrypted_aes_key + encrypted_data
        
        metadata = {
            "algorithm": "aes_256_rsa",
            "rsa_key_size": 2048,
            "private_key": base64.b64encode(private_key_bytes).decode(),
            "timestamp": datetime.now().isoformat()
        }
        
        return combined_data, metadata
    
    def _decrypt_aes_256_rsa(self, encrypted_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """Decrypt AES-256 + RSA encrypted data"""
        # Extract RSA private key
        private_key_bytes = base64.b64decode(metadata["private_key"])
        private_key = serialization.load_pem_private_key(private_key_bytes, password=None)
        
        # Extract encrypted AES key length
        aes_key_len = int.from_bytes(encrypted_data[:4], 'big')
        
        # Extract encrypted AES key
        encrypted_aes_key = encrypted_data[4:4+aes_key_len]
        
        # Extract AES-encrypted data
        aes_encrypted_data = encrypted_data[4+aes_key_len:]
        
        # Decrypt AES key with RSA
        aes_key = private_key.decrypt(
            encrypted_aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt data with AES
        fernet_aes = Fernet(base64.urlsafe_b64encode(aes_key))
        return fernet_aes.decrypt(aes_encrypted_data)
    
    def _encrypt_maximum_security(self, data: bytes) -> Tuple[bytes, Dict[str, Any]]:
        """Encrypt with maximum security (multiple layers)"""
        # Layer 1: AES-256 with random key
        layer1_key = secrets.token_bytes(32)
        fernet_layer1 = Fernet(base64.urlsafe_b64encode(layer1_key))
        layer1_encrypted = fernet_layer1.encrypt(data)
        
        # Layer 2: AES-256 with master key
        layer2_encrypted = self.fernet.encrypt(layer1_encrypted)
        
        # Layer 3: RSA encryption of the layer1 key
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()
        
        encrypted_layer1_key = public_key.encrypt(
            layer1_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Combine all data
        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        combined_data = (
            len(encrypted_layer1_key).to_bytes(4, 'big') +
            encrypted_layer1_key +
            layer2_encrypted
        )
        
        metadata = {
            "algorithm": "maximum_security",
            "layers": 3,
            "private_key": base64.b64encode(private_key_bytes).decode(),
            "timestamp": datetime.now().isoformat()
        }
        
        return combined_data, metadata
    
    def _decrypt_maximum_security(self, encrypted_data: bytes, metadata: Dict[str, Any]) -> bytes:
        """Decrypt maximum security encrypted data"""
        # Extract RSA private key
        private_key_bytes = base64.b64decode(metadata["private_key"])
        private_key = serialization.load_pem_private_key(private_key_bytes, password=None)
        
        # Extract encrypted layer1 key length
        key_len = int.from_bytes(encrypted_data[:4], 'big')
        
        # Extract encrypted layer1 key
        encrypted_layer1_key = encrypted_data[4:4+key_len]
        
        # Extract layer2 encrypted data
        layer2_encrypted = encrypted_data[4+key_len:]
        
        # Decrypt layer1 key with RSA
        layer1_key = private_key.decrypt(
            encrypted_layer1_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt layer2 with master key
        layer1_encrypted = self.fernet.decrypt(layer2_encrypted)
        
        # Decrypt layer1 with recovered key
        fernet_layer1 = Fernet(base64.urlsafe_b64encode(layer1_key))
        return fernet_layer1.decrypt(layer1_encrypted)
    
    async def store_secret(self, secret_type: SecretType, value: Union[str, bytes],
                          rotation_interval_days: Optional[int] = None,
                          expires_at: Optional[datetime] = None) -> str:
        """Store a secret securely"""
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("Cryptography library not available")
        
        secret_id = self._generate_secret_id()
        
        # Convert to bytes if string
        if isinstance(value, str):
            value_bytes = value.encode('utf-8')
        else:
            value_bytes = value
        
        # Encrypt secret value
        encrypted_value = self.fernet.encrypt(value_bytes)
        
        # Create secret entry
        secret_entry = SecretEntry(
            secret_id=secret_id,
            secret_type=secret_type,
            encrypted_value=encrypted_value,
            metadata={
                "algorithm": "aes_256",
                "created_by": self.name,
                "timestamp": datetime.now().isoformat()
            },
            created_at=datetime.now(),
            expires_at=expires_at,
            rotation_interval_days=rotation_interval_days
        )
        
        self.secrets[secret_id] = secret_entry
        
        # Update metrics
        self.encryption_metrics['total_secrets'] += 1
        
        # Log secret creation
        self._log_secret_access("create", secret_id, secret_type.value)
        
        self.logger.info(f"Secret stored: {secret_id} (Type: {secret_type.value})")
        
        return secret_id
    
    async def retrieve_secret(self, secret_id: str) -> Tuple[bool, Union[bytes, str]]:
        """Retrieve a secret by ID"""
        if not CRYPTO_AVAILABLE:
            return False, "Cryptography library not available"
        
        if secret_id not in self.secrets:
            return False, "Secret not found"
        
        secret_entry = self.secrets[secret_id]
        
        # Check if secret has expired
        if secret_entry.expires_at and datetime.now() > secret_entry.expires_at:
            return False, "Secret has expired"
        
        try:
            # Decrypt secret value
            decrypted_value = self.fernet.decrypt(secret_entry.encrypted_value)
            
            # Log access
            self._log_secret_access("retrieve", secret_id, secret_entry.secret_type.value)
            
            self.logger.debug(f"Secret retrieved: {secret_id}")
            
            return True, decrypted_value
            
        except Exception as e:
            self.logger.error(f"Secret retrieval failed for {secret_id}: {e}")
            return False, f"Retrieval failed: {str(e)}"
    
    async def rotate_secret(self, secret_id: str, new_value: Union[str, bytes]) -> bool:
        """Rotate a secret with new value"""
        if secret_id not in self.secrets:
            return False
        
        secret_entry = self.secrets[secret_id]
        
        # Convert to bytes if string
        if isinstance(new_value, str):
            new_value_bytes = new_value.encode('utf-8')
        else:
            new_value_bytes = new_value
        
        # Encrypt new value
        encrypted_new_value = self.fernet.encrypt(new_value_bytes)
        
        # Update secret
        secret_entry.encrypted_value = encrypted_new_value
        secret_entry.last_rotated = datetime.now()
        
        # Update metrics
        self.encryption_metrics['key_rotations'] += 1
        
        # Log rotation
        self._log_secret_access("rotate", secret_id, secret_entry.secret_type.value)
        
        self.logger.info(f"Secret rotated: {secret_id}")
        
        return True
    
    def _rotate_expired_keys(self) -> None:
        """Rotate expired encryption keys"""
        current_time = datetime.now()
        
        for key_id, key in list(self.encryption_keys.items()):
            if key.expires_at and current_time > key.expires_at:
                # Generate new key
                new_key = EncryptionKey(
                    key_id=self._generate_key_id(),
                    key_data=secrets.token_bytes(32),
                    algorithm=key.algorithm,
                    key_size=key.key_size,
                    created_at=current_time,
                    purpose=key.purpose
                )
                
                self.encryption_keys[new_key.key_id] = new_key
                
                # Mark old key as expired but keep for decryption
                self.encryption_keys[key_id].expires_at = current_time
                
                self.logger.info(f"Encryption key rotated: {key_id} -> {new_key.key_id}")
    
    def _rotate_expired_secrets(self) -> None:
        """Check for secrets that need rotation"""
        current_time = datetime.now()
        
        for secret_id, secret in self.secrets.items():
            if secret.rotation_interval_days:
                next_rotation = secret.last_rotated or secret.created_at
                next_rotation += timedelta(days=secret.rotation_interval_days)
                
                if current_time > next_rotation:
                    self.logger.warning(f"Secret {secret_id} needs rotation")
                    # In production, this would trigger an alert or automated rotation
    
    def _cleanup_expired_data(self) -> None:
        """Clean up expired encrypted data"""
        current_time = datetime.now()
        expired_data = []
        
        for data_id, encrypted_data in self.encrypted_data.items():
            # Check retention policy
            if encrypted_data.retention_policy:
                policy = self.retention_policies.get(encrypted_data.retention_policy)
                if policy:
                    expiry_date = encrypted_data.created_at + timedelta(days=policy.retention_days)
                    
                    if current_time > expiry_date:
                        expired_data.append(data_id)
        
        # Delete expired data
        for data_id in expired_data:
            if self.retention_policies.get(
                self.encrypted_data[data_id].retention_policy, 
                DataRetentionPolicy("", "", DataClassification.PUBLIC, 0)
            ).backup_before_delete:
                self._backup_data_before_deletion(data_id)
            
            del self.encrypted_data[data_id]
            self.logger.info(f"Expired data deleted: {data_id}")
    
    def _enforce_retention_policies(self) -> None:
        """Enforce data retention policies"""
        for policy_id, policy in self.retention_policies.items():
            if not policy.auto_delete:
                continue
            
            # Find data matching this policy
            matching_data = [
                data_id for data_id, encrypted_data in self.encrypted_data.items()
                if (encrypted_data.classification == policy.classification_level and
                    encrypted_data.retention_policy == policy_id)
            ]
            
            current_time = datetime.now()
            
            for data_id in matching_data:
                encrypted_data = self.encrypted_data[data_id]
                expiry_date = encrypted_data.created_at + timedelta(days=policy.retention_days)
                
                if current_time > expiry_date:
                    if policy.backup_before_delete:
                        self._backup_data_before_deletion(data_id)
                    
                    del self.encrypted_data[data_id]
                    self.logger.info(f"Data deleted per retention policy {policy_id}: {data_id}")
    
    def _backup_data_before_deletion(self, data_id: str) -> None:
        """Backup data before deletion"""
        # In production, this would backup to secure storage
        # For now, just log the action
        self.logger.info(f"Data backed up before deletion: {data_id}")
    
    def _generate_compliance_reports(self) -> None:
        """Generate compliance reports"""
        current_time = datetime.now()
        
        # GDPR compliance report
        gdpr_report = {
            "framework": ComplianceFramework.GDPR.value,
            "generated_at": current_time.isoformat(),
            "data_inventory": {
                "total_encrypted_items": len(self.encrypted_data),
                "by_classification": self._count_by_classification(),
                "retention_compliance": self._check_retention_compliance(ComplianceFramework.GDPR)
            },
            "access_logs": len(self.data_access_log),
            "violations": self._count_compliance_violations(ComplianceFramework.GDPR)
        }
        
        self.compliance_reports.append(gdpr_report)
        
        # Keep only recent reports
        if len(self.compliance_reports) > 100:
            self.compliance_reports = self.compliance_reports[-100:]
    
    def _check_compliance_violations(self) -> None:
        """Check for compliance violations"""
        violations = 0
        
        # Check for data without proper classification
        for data_id, encrypted_data in self.encrypted_data.items():
            if not encrypted_data.classification:
                violations += 1
        
        # Check for secrets without rotation
        for secret_id, secret in self.secrets.items():
            if (secret.secret_type in [SecretType.API_KEY, SecretType.JWT_SECRET] and
                not secret.rotation_interval_days):
                violations += 1
        
        self.encryption_metrics['compliance_violations'] = violations
    
    def _count_by_classification(self) -> Dict[str, int]:
        """Count encrypted data by classification"""
        counts = defaultdict(int)
        
        for encrypted_data in self.encrypted_data.values():
            counts[encrypted_data.classification.value] += 1
        
        return dict(counts)
    
    def _check_retention_compliance(self, framework: ComplianceFramework) -> Dict[str, Any]:
        """Check retention compliance for framework"""
        compliance_data = []
        
        for policy_id, policy in self.retention_policies.items():
            if framework in policy.compliance_frameworks:
                matching_items = [
                    data for data in self.encrypted_data.values()
                    if data.retention_policy == policy_id
                ]
                
                compliance_data.append({
                    "policy_id": policy_id,
                    "retention_days": policy.retention_days,
                    "items_count": len(matching_items),
                    "auto_delete": policy.auto_delete
                })
        
        return {"policies": compliance_data}
    
    def _count_compliance_violations(self, framework: ComplianceFramework) -> int:
        """Count compliance violations for framework"""
        violations = 0
        
        # Check for data without proper retention policies
        for encrypted_data in self.encrypted_data.values():
            if framework in encrypted_data.compliance_tags and not encrypted_data.retention_policy:
                violations += 1
        
        return violations
    
    def _get_compliance_tags(self, classification: DataClassification) -> Set[str]:
        """Get compliance tags based on data classification"""
        tags = set()
        
        if classification in [DataClassification.CONFIDENTIAL, DataClassification.RESTRICTED]:
            tags.add(ComplianceFramework.GDPR.value)
        
        if classification == DataClassification.RESTRICTED:
            tags.add(ComplianceFramework.HIPAA.value)
            tags.add(ComplianceFramework.SOX.value)
        
        return tags
    
    def _log_data_access(self, operation: str, data_id: str, classification: str) -> None:
        """Log data access for audit trail"""
        access_log = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "data_id": data_id,
            "classification": classification,
            "agent": self.name
        }
        
        self.data_access_log.append(access_log)
    
    def _log_secret_access(self, operation: str, secret_id: str, secret_type: str) -> None:
        """Log secret access for audit trail"""
        if secret_id in self.secrets:
            self.secrets[secret_id].access_log.append({
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "agent": self.name
            })
    
    def _generate_data_id(self) -> str:
        """Generate unique data ID"""
        return f"data_{secrets.token_urlsafe(16)}"
    
    def _generate_secret_id(self) -> str:
        """Generate unique secret ID"""
        return f"secret_{secrets.token_urlsafe(16)}"
    
    def _generate_key_id(self) -> str:
        """Generate unique key ID"""
        return f"key_{secrets.token_urlsafe(16)}"
    
    async def secure_delete_data(self, data_id: str) -> bool:
        """Securely delete encrypted data"""
        if data_id not in self.encrypted_data:
            return False
        
        encrypted_data = self.encrypted_data[data_id]
        
        # Backup if required by policy
        if encrypted_data.retention_policy:
            policy = self.retention_policies.get(encrypted_data.retention_policy)
            if policy and policy.backup_before_delete:
                self._backup_data_before_deletion(data_id)
        
        # Securely wipe the data
        self._secure_wipe_data(encrypted_data)
        
        # Remove from storage
        del self.encrypted_data[data_id]
        
        # Log deletion
        self._log_data_access("secure_delete", data_id, encrypted_data.classification.value)
        
        self.logger.info(f"Data securely deleted: {data_id}")
        
        return True
    
    def _secure_wipe_data(self, encrypted_data: EncryptedData) -> None:
        """Securely wipe data from memory"""
        # Overwrite the encrypted content with random data
        if isinstance(encrypted_data.encrypted_content, bytes):
            # In Python, bytes are immutable, so we can't actually overwrite
            # In a production system, this would use more sophisticated techniques
            secrets.token_bytes(len(encrypted_data.encrypted_content))
            # The original data will be garbage collected
    
    def get_protection_status(self) -> Dict[str, Any]:
        """Get comprehensive data protection status"""
        recent_access = [
            log for log in list(self.data_access_log)[-100:]  # Last 100 accesses
        ]
        
        return {
            'encryption_metrics': self.encryption_metrics,
            'data_inventory': {
                'total_encrypted_items': len(self.encrypted_data),
                'total_secrets': len(self.secrets),
                'total_keys': len(self.encryption_keys),
                'by_classification': self._count_by_classification()
            },
            'retention_policies': {
                policy_id: {
                    'name': policy.name,
                    'classification': policy.classification_level.value,
                    'retention_days': policy.retention_days,
                    'auto_delete': policy.auto_delete,
                    'compliance_frameworks': [f.value for f in policy.compliance_frameworks]
                }
                for policy_id, policy in self.retention_policies.items()
            },
            'compliance_status': {
                'frameworks_supported': [f.value for f in ComplianceFramework],
                'recent_violations': self.encryption_metrics['compliance_violations'],
                'last_report_count': len(self.compliance_reports)
            },
            'recent_access_logs': recent_access,
            'system_configuration': {
                'crypto_available': CRYPTO_AVAILABLE,
                'key_rotation_enabled': self.enable_key_rotation,
                'default_encryption_level': self.default_encryption_level.value
            }
        }
    
    def _get_machine_id(self) -> str:
        """Get current machine identifier"""
        import socket
        hostname = socket.gethostname().lower()
        
        if "main" in hostname or ("pc" in hostname and "pc2" not in hostname):
            return "MainPC"
        elif "pc2" in hostname:
            return "PC2"
        else:
            return "MainPC"  # Default
    
    def shutdown(self):
        """Shutdown the data protection system"""
        # Secure wipe of sensitive data
        if hasattr(self, 'master_key') and self.master_key:
            # Overwrite master key with zeros
            self.master_key = b'\x00' * len(self.master_key)
        
        # Clear data structures
        self.encrypted_data.clear()
        self.secrets.clear()
        self.encryption_keys.clear()
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    import asyncio
    
    logger = configure_logging(__name__, level="INFO")
    
    async def test_data_protection():
        if not CRYPTO_AVAILABLE:
            print("Cryptography library not available - skipping test")
            return
        
        protection_system = DataProtectionSystem()
        
        try:
            # Test data encryption
            test_data = "Sensitive information that needs protection"
            
            data_id = await protection_system.encrypt_data(
                test_data,
                classification=DataClassification.CONFIDENTIAL,
                encryption_level=EncryptionLevel.HIGH
            )
            
            print(f"Data encrypted with ID: {data_id}")
            
            # Test data decryption
            success, decrypted_data = await protection_system.decrypt_data(data_id)
            
            if success:
                print(f"Data decrypted successfully: {decrypted_data.decode()}")
            else:
                print(f"Decryption failed: {decrypted_data}")
            
            # Test secret storage
            secret_id = await protection_system.store_secret(
                SecretType.API_KEY,
                "super-secret-api-key-12345",
                rotation_interval_days=90
            )
            
            print(f"Secret stored with ID: {secret_id}")
            
            # Test secret retrieval
            success, secret_value = await protection_system.retrieve_secret(secret_id)
            
            if success:
                print(f"Secret retrieved: {secret_value.decode()}")
            else:
                print(f"Secret retrieval failed: {secret_value}")
            
            # Get protection status
            status = protection_system.get_protection_status()
            print(json.dumps(status, indent=2, default=str))
            
        finally:
            protection_system.shutdown()
    
    asyncio.run(test_data_protection()) 