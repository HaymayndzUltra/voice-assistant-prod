#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
"""
WP-10 Security & Authentication Migration Script
Migrates agents to use authentication, encryption, and access control
Target: All agents for comprehensive security
"""

import os
import ast
import re
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class SecurityAnalyzer(ast.NodeVisitor):
    """AST analyzer to detect security opportunities and vulnerabilities"""
    
    def __init__(self):
        self.auth_patterns = []
        self.encryption_patterns = []
        self.api_endpoints = []
        self.data_operations = []
        self.network_operations = []
        self.file_operations = []
        self.vulnerabilities = []
        self.security_score = 0
        
    def visit_FunctionDef(self, node):
        # Check for authentication needs
        has_auth = False
        has_encryption = False
        
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # Look for API/HTTP operations
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['get', 'post', 'put', 'delete', 'request']):
                    self.api_endpoints.append(f"HTTP operation in {node.name} (line {child.lineno})")
                    self.security_score += 3
                
                # Look for authentication patterns
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['authenticate', 'login', 'verify', 'authorize']):
                    has_auth = True
                    self.auth_patterns.append(f"Auth operation in {node.name} (line {child.lineno})")
                
                # Look for encryption patterns
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['encrypt', 'decrypt', 'hash', 'sign']):
                    has_encryption = True
                    self.encryption_patterns.append(f"Encryption in {node.name} (line {child.lineno})")
                
                # Look for data operations
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['save', 'store', 'write', 'update']):
                    self.data_operations.append(f"Data operation in {node.name} (line {child.lineno})")
                    self.security_score += 1
                
                # Look for file operations
                if (isinstance(child.func, ast.Name) and 
                    child.func.id in ['open', 'read', 'write']):
                    self.file_operations.append(f"File operation in {node.name} (line {child.lineno})")
                    self.security_score += 1
                
                # Look for network operations
                if (isinstance(child.func, ast.Attribute) and 
                    child.func.attr in ['connect', 'send', 'receive', 'socket']):
                    self.network_operations.append(f"Network operation in {node.name} (line {child.lineno})")
                    self.security_score += 2
        
        # Check for potential vulnerabilities
        if len(self.api_endpoints) > 0 and not has_auth:
            self.vulnerabilities.append(f"Unprotected API operations in {node.name}")
            self.security_score += 5
        
        if len(self.data_operations) > 0 and not has_encryption:
            self.vulnerabilities.append(f"Unencrypted data operations in {node.name}")
            self.security_score += 3
        
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # Look for hardcoded secrets/passwords
        if isinstance(node.func, ast.Name):
            for arg in node.args:
                if isinstance(arg, ast.Str):
                    value = arg.s.lower()
                    if any(keyword in value for keyword in ['password', 'secret', 'key', 'token']):
                        if len(arg.s) > 8:  # Potential hardcoded secret
                            self.vulnerabilities.append(f"Potential hardcoded secret (line {node.lineno})")
                            self.security_score += 8
        
        self.generic_visit(node)

def find_security_candidates() -> List[Path]:
    """Find agents that need security implementation"""
    root = Path.cwd()
    agent_files = []
    
    search_dirs = [
        "main_pc_code/agents",
        "pc2_code/agents", 
        "common",
        "phase1_implementation",
        "phase2_implementation"
    ]
    
    for search_dir in search_dirs:
        search_path = root / search_dir
        if search_path.exists():
            for python_file in search_path.rglob("*.py"):
                if (python_file.name != "__init__.py" and 
                    not python_file.name.startswith("test_") and
                    "_test" not in python_file.name):
                    agent_files.append(python_file)
    
    return agent_files

def analyze_security_needs(file_path: Path) -> Dict:
    """Analyze a file for security needs"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        tree = ast.parse(content)
        analyzer = SecurityAnalyzer()
        analyzer.visit(tree)
        
        # Additional pattern-based analysis
        content_lower = content.lower()
        
        # Authentication patterns
        auth_keywords = len(re.findall(r'(auth|login|token|jwt|session|credential)', content_lower))
        
        # Encryption patterns
        encryption_keywords = len(re.findall(r'(encrypt|decrypt|hash|cipher|crypto|ssl|tls)', content_lower))
        
        # Security patterns
        security_keywords = len(re.findall(r'(security|secure|protect|permission|access|role)', content_lower))
        
        # API patterns
        api_patterns = len(re.findall(r'(api|endpoint|request|response|http)', content_lower))
        
        # Database patterns
        db_patterns = len(re.findall(r'(database|sql|query|insert|update|delete)', content_lower))
        
        # Network patterns
        network_patterns = len(re.findall(r'(socket|network|tcp|udp|connection)', content_lower))
        
        # Calculate needs
        needs_authentication = (len(analyzer.api_endpoints) > 0 or 
                               api_patterns > 2 or 
                               auth_keywords < 2 and analyzer.security_score > 5)
        
        needs_encryption = (len(analyzer.data_operations) > 0 or 
                           db_patterns > 1 or 
                           len(analyzer.file_operations) > 2 or
                           encryption_keywords < 1 and analyzer.security_score > 8)
        
        needs_access_control = (len(analyzer.api_endpoints) > 1 or 
                               network_patterns > 1 or
                               analyzer.security_score > 10)
        
        needs_rate_limiting = (api_patterns > 3 or 
                              len(analyzer.api_endpoints) > 2)
        
        # Calculate priority based on vulnerabilities and exposure
        if len(analyzer.vulnerabilities) > 3:
            priority = "critical"
        elif analyzer.security_score > 20 or len(analyzer.vulnerabilities) > 1:
            priority = "high"
        elif analyzer.security_score > 10:
            priority = "medium"
        else:
            priority = "low"
        
        return {
            'file_path': file_path,
            'auth_patterns': analyzer.auth_patterns,
            'encryption_patterns': analyzer.encryption_patterns,
            'api_endpoints': analyzer.api_endpoints,
            'data_operations': analyzer.data_operations,
            'network_operations': analyzer.network_operations,
            'file_operations': analyzer.file_operations,
            'vulnerabilities': analyzer.vulnerabilities,
            'auth_keywords': auth_keywords,
            'encryption_keywords': encryption_keywords,
            'security_keywords': security_keywords,
            'api_count': api_patterns,
            'db_count': db_patterns,
            'network_count': network_patterns,
            'security_score': analyzer.security_score + len(analyzer.vulnerabilities) * 5,
            'needs_authentication': needs_authentication,
            'needs_encryption': needs_encryption,
            'needs_access_control': needs_access_control,
            'needs_rate_limiting': needs_rate_limiting,
            'priority': priority,
            'vulnerability_count': len(analyzer.vulnerabilities)
        }
    
    except Exception as e:
        return {
            'file_path': file_path,
            'error': str(e),
            'security_score': 0,
            'needs_authentication': False,
            'needs_encryption': False,
            'needs_access_control': False,
            'needs_rate_limiting': False,
            'priority': 'low',
            'vulnerability_count': 0
        }

def generate_authentication_integration(file_path: Path) -> str:
    """Generate authentication integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-10 Authentication Integration for {agent_name}
# Add comprehensive authentication and authorization

from common.security.authentication import (
    get_security_manager, SecurityContext, AuthenticationMethod,
    require_auth, ResourceType, PermissionLevel
)

class {agent_name.title().replace("_", "")}AuthenticationIntegration:
    """Authentication integration for {agent_name}"""
    
    def __init__(self):
        self.security_manager = get_security_manager()
        
        # Create agent-specific API key
        key_id, api_key = self.security_manager.create_api_key(
            name="{agent_name}_service_key",
            permissions={{
                "agent:read", "agent:write", "agent:execute",
                "api:read", "api:write", "data:read", "data:write"
            }},
            rate_limit=100  # requests per minute
        )
        
        # Store API key securely (in production, use secrets manager)
        self.api_key = api_key
        print(f"Generated API key for {agent_name}: {{key_id}}")
    
    async def authenticate_request(self, request_headers: dict) -> SecurityContext:
        """Authenticate incoming request"""
        
        # Try JWT authentication
        auth_header = request_headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            context = await self.security_manager.authenticate(
                AuthenticationMethod.JWT,
                {{"token": token}}
            )
            if context:
                return context
        
        # Try API key authentication
        api_key = request_headers.get("X-API-Key")
        if api_key:
            context = await self.security_manager.authenticate(
                AuthenticationMethod.API_KEY,
                {{"api_key": api_key}},
                request_info={{
                    "ip_address": request_headers.get("X-Real-IP", "unknown"),
                    "user_agent": request_headers.get("User-Agent", "unknown")
                }}
            )
            if context:
                return context
        
        # Try HMAC authentication for system-to-system
        signature = request_headers.get("X-Signature")
        timestamp = request_headers.get("X-Timestamp")
        if signature and timestamp:
            context = await self.security_manager.authenticate(
                AuthenticationMethod.HMAC,
                {{
                    "method": "POST",
                    "path": "/api/{agent_name}",
                    "body": "",  # Request body
                    "timestamp": timestamp,
                    "signature": signature
                }}
            )
            if context:
                return context
        
        return None
    
    @require_auth(resource=ResourceType.AGENT, action=PermissionLevel.READ)
    async def get_agent_status(self, security_context: SecurityContext):
        """Get agent status - requires read permission"""
        return {{
            "agent_id": "{agent_name}",
            "status": "running",
            "authenticated_user": security_context.user_id,
            "permissions": list(security_context.permissions)
        }}
    
    @require_auth(resource=ResourceType.AGENT, action=PermissionLevel.EXECUTE)
    async def execute_operation(self, operation: str, data: dict, 
                               security_context: SecurityContext):
        """Execute operation - requires execute permission"""
        
        # Log security context
        print(f"User {{security_context.user_id}} executing {{operation}}")
        
        # Check specific operation permissions
        if operation == "sensitive_operation":
            if not security_context.has_role("admin"):
                raise PermissionError("Admin role required for sensitive operations")
        
        # Perform operation
        result = await self.perform_operation(operation, data)
        
        return {{
            "operation": operation,
            "result": result,
            "executed_by": security_context.user_id,
            "timestamp": time.time()
        }}
    
    @require_auth(resource=ResourceType.DATA, action=PermissionLevel.WRITE)
    async def update_data(self, data_id: str, data: dict,
                         security_context: SecurityContext):
        """Update data - requires write permission"""
        
        # Additional authorization check
        if not self.security_manager.authorize(
            security_context, 
            ResourceType.DATA, 
            PermissionLevel.WRITE
        ):
            raise PermissionError("Insufficient permissions for data update")
        
        # Audit log
        print(f"Data update by {{security_context.user_id}}: {{data_id}}")
        
        # Perform update
        result = await self.update_database(data_id, data)
        
        return result
    
    def generate_user_token(self, user_id: str, roles: set = None) -> str:
        """Generate authentication token for user"""
        
        # Default roles for this agent
        default_roles = {{"viewer", "operator"}}
        effective_roles = roles or default_roles
        
        # Generate JWT token
        token = self.security_manager.generate_token(
            user_id=user_id,
            roles=effective_roles,
            expires_in=timedelta(hours=24)
        )
        
        return token
    
    def create_service_account(self, service_name: str, permissions: set) -> tuple:
        """Create service account with API key"""
        
        key_id, api_key = self.security_manager.create_api_key(
            name=f"{{service_name}}_service",
            permissions=permissions,
            expires_in=timedelta(days=365),  # 1 year
            rate_limit=1000  # requests per minute
        )
        
        return key_id, api_key
    
    async def verify_request_integrity(self, request_data: dict, 
                                     signature: str, timestamp: str) -> bool:
        """Verify request integrity using HMAC"""
        
        # Check timestamp (prevent replay attacks)
        try:
            request_time = float(timestamp)
            if abs(time.time() - request_time) > 300:  # 5 minutes
                return False
        except ValueError:
            return False
        
        # Verify HMAC signature
        return self.security_manager.hmac_validator.verify_signature(
            method="POST",
            path=f"/api/{agent_name}",
            body=json.dumps(request_data, sort_keys=True),
            timestamp=timestamp,
            received_signature=signature
        )

# Example usage:
# auth_integration = {agent_name.title().replace("_", "")}AuthenticationIntegration()
# 
# # In your request handler:
# security_context = await auth_integration.authenticate_request(request.headers)
# if not security_context:
#     raise HTTPException(401, "Authentication required")
# 
# # Use protected methods:
# status = await auth_integration.get_agent_status(security_context=security_context)
# result = await auth_integration.execute_operation("process_data", data, security_context=security_context)
'''
    
    return integration_example

def generate_encryption_integration(file_path: Path) -> str:
    """Generate encryption integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-10 Encryption Integration for {agent_name}
# Add data encryption and secrets management

from common.security.encryption import (
    get_encryption_service, get_secrets_manager, 
    EncryptionAlgorithm, encrypt_data, decrypt_data,
    set_secret, get_secret
)

class {agent_name.title().replace("_", "")}EncryptionIntegration:
    """Encryption integration for {agent_name}"""
    
    def __init__(self):
        self.encryption_service = get_encryption_service()
        self.secrets_manager = get_secrets_manager()
        
        # Generate encryption keys for different purposes
        self.data_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.AES_256_GCM,
            purpose="{agent_name}_data"
        )
        
        self.file_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.FERNET,
            purpose="{agent_name}_files"
        )
        
        # Setup application secrets
        self._setup_secrets()
    
    def _setup_secrets(self):
        """Setup application secrets"""
        # Store configuration secrets
        set_secret("{agent_name}_db_connection", {{
            "host": "localhost",
            "port": 5432,
            "database": "{agent_name}_db",
            "username": "app_user",
            "password": "secure_password_123"
        }})
        
        set_secret("{agent_name}_api_config", {{
            "external_api_key": "sk_live_abc123xyz789",
            "webhook_secret": "whsec_secret_key_456",
            "encryption_key": "enc_key_789"
        }})
    
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
                encrypted_data[field] = {{
                    "encrypted": True,
                    "data": encrypted.to_dict()
                }}
        
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
        output_file = output_path or f"{{file_path}}.encrypted"
        with open(output_file, 'w') as f:
            json.dump(encrypted.to_dict(), f)
        
        print(f"File encrypted: {{file_path}} -> {{output_file}}")
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
        
        print(f"File decrypted: {{encrypted_file_path}} -> {{output_file}}")
        return output_file
    
    def get_database_credentials(self) -> dict:
        """Get database credentials from secrets manager"""
        return get_secret("{agent_name}_db_connection")
    
    def get_api_configuration(self) -> dict:
        """Get API configuration from secrets manager"""
        return get_secret("{agent_name}_api_config")
    
    async def secure_data_storage(self, data_id: str, data: dict):
        """Store data with encryption"""
        
        # Encrypt sensitive data
        encrypted_data = await self.encrypt_sensitive_data(data)
        
        # Add metadata
        stored_data = {{
            "data_id": data_id,
            "encrypted_at": time.time(),
            "encryption_key_id": self.data_key_id,
            "data": encrypted_data
        }}
        
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
            purpose="{agent_name}_data"
        )
        
        self.file_key_id = self.encryption_service.key_manager.generate_key(
            EncryptionAlgorithm.FERNET,
            purpose="{agent_name}_files"
        )
        
        print(f"Rotated encryption keys:")
        print(f"  Data key: {{old_data_key}} -> {{self.data_key_id}}")
        print(f"  File key: {{old_file_key}} -> {{self.file_key_id}}")
        
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
        
        return {{
            "encrypted_message": encrypted_message.to_dict(),
            "key_id": temp_key_id,
            "sender": "{agent_name}",
            "timestamp": time.time()
        }}

# Example usage:
# encryption = {agent_name.title().replace("_", "")}EncryptionIntegration()
# 
# # Encrypt sensitive data
# sensitive_data = {{"username": "admin", "password": "secret123"}}
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
'''
    
    return integration_example

def generate_access_control_integration(file_path: Path) -> str:
    """Generate access control integration example"""
    agent_name = file_path.stem
    
    integration_example = f'''
# WP-10 Access Control Integration for {agent_name}
# Add rate limiting, IP filtering, and security monitoring

from common.security.access_control import (
from common.env_helpers import get_env
    get_access_control_engine, get_security_middleware,
    protect_endpoint, AccessDecision, ThreatLevel,
    add_ip_to_blacklist, add_ip_to_whitelist, check_rate_limit
)

class {agent_name.title().replace("_", "")}AccessControlIntegration:
    """Access control integration for {agent_name}"""
    
    def __init__(self):
        self.access_control = get_access_control_engine()
        self.security_middleware = get_security_middleware()
        
        # Setup agent-specific rules
        self._setup_access_rules()
        self._setup_rate_limits()
        self._setup_ip_controls()
    
    def _setup_access_rules(self):
        """Setup access control rules"""
        from common.security.access_control import AccessRule
        
        # Block requests from known bad user agents
        self.access_control.add_rule(AccessRule(
            name="{agent_name}_block_bots",
            priority=50,
            conditions={{
                "user_agent": {{
                    "regex": r".*(bot|crawler|scraper|spider).*"
                }}
            }},
            action=AccessDecision.DENY
        ))
        
        # Throttle high-frequency requests
        self.access_control.add_rule(AccessRule(
            name="{agent_name}_throttle_high_freq",
            priority=100,
            conditions={{
                "request_count_per_minute": {{
                    "range": [50, float('inf')]
                }}
            }},
            action=AccessDecision.THROTTLE
        ))
        
        # Allow admin bypass
        self.access_control.add_rule(AccessRule(
            name="{agent_name}_admin_bypass",
            priority=1,
            conditions={{
                "roles": ["admin", "system"]
            }},
            action=AccessDecision.ALLOW
        ))
        
        # Block suspicious patterns
        self.access_control.add_rule(AccessRule(
            name="{agent_name}_block_suspicious",
            priority=75,
            conditions={{
                "path": {{
                    "regex": r".*(admin|config|\.env|\.git|backup).*"
                }},
                "roles": []  # No roles (unauthenticated)
            }},
            action=AccessDecision.DENY
        ))
    
    def _setup_rate_limits(self):
        """Setup rate limiting rules"""
        from common.security.access_control import RateLimitRule, RateLimitType
        
        # API rate limits
        self.access_control.rate_limiter.add_rule(RateLimitRule(
            name="{agent_name}_api_requests",
            limit_type=RateLimitType.REQUESTS_PER_MINUTE,
            max_requests=60,
            time_window=60,
            burst_allowance=10
        ))
        
        # Authentication attempts
        self.access_control.rate_limiter.add_rule(RateLimitRule(
            name="{agent_name}_auth_attempts",
            limit_type=RateLimitType.REQUESTS_PER_MINUTE,
            max_requests=5,
            time_window=60,
            burst_allowance=0
        ))
        
        # Hourly limits
        self.access_control.rate_limiter.add_rule(RateLimitRule(
            name="{agent_name}_hourly_requests",
            limit_type=RateLimitType.REQUESTS_PER_HOUR,
            max_requests=1000,
            time_window=3600,
            burst_allowance=50
        ))
    
    def _setup_ip_controls(self):
        """Setup IP-based access control"""
        
        # Whitelist internal networks
        add_ip_to_whitelist("10.0.0.0/8")      # Private networks
        add_ip_to_whitelist("172.16.0.0/12")   # Private networks
        add_ip_to_whitelist("192.168.0.0/16")  # Private networks
        add_ip_to_whitelist("127.0.0.0/8")     # Localhost
        
        # Blacklist known malicious IPs (examples)
        add_ip_to_blacklist("192.0.2.0/24")    # RFC 5737 test network
        add_ip_to_blacklist("198.51.100.0/24") # RFC 5737 test network
    
    @protect_endpoint(
        rate_limit_rule="{agent_name}_api_requests",
        require_auth=True,
        allowed_roles=["user", "operator", "admin"]
    )
    async def protected_api_endpoint(self, request, security_context):
        """Protected API endpoint with access control"""
        
        # Extract request info
        user_id = security_context.user_id
        ip_address = getattr(request, "client", {{}}).get("host", "unknown")
        
        print(f"API request from {{user_id}} ({{ip_address}})")
        
        # Your endpoint logic here
        return {{
            "message": "Access granted",
            "user": user_id,
            "timestamp": time.time()
        }}
    
    async def check_request_security(self, request_info: dict) -> tuple:
        """Check request security and return decision"""
        
        # Build context for access control
        context = {{
            "ip_address": request_info.get("ip_address", ""),
            "user_agent": request_info.get("user_agent", ""),
            "user_id": request_info.get("user_id"),
            "agent_id": "{agent_name}",
            "roles": request_info.get("roles", []),
            "path": request_info.get("path", ""),
            "method": request_info.get("method", "GET")
        }}
        
        # Check access control
        allowed, info = await self.security_middleware.process_request(context)
        
        return allowed, info
    
    def monitor_security_events(self) -> dict:
        """Get security monitoring summary"""
        
        events = self.access_control.get_security_events(limit=100)
        summary = self.access_control.get_security_summary()
        
        # Analyze recent threats
        recent_threats = [
            event for event in events 
            if event.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        ]
        
        return {{
            "summary": summary,
            "recent_threats": len(recent_threats),
            "total_events": len(events),
            "threat_breakdown": {{
                level.value: len([e for e in events if e.threat_level == level])
                for level in ThreatLevel
            }}
        }}
    
    def add_temporary_block(self, ip_address: str, duration_minutes: int = 60):
        """Add temporary IP block"""
        from common.security.access_control import AccessRule
        import time
        
        # Create temporary rule
        rule = AccessRule(
            name=f"temp_block_{{ip_address.replace('.', '_')}}",
            priority=10,
            conditions={{"ip_address": ip_address}},
            action=AccessDecision.DENY,
            expires_at=time.time() + (duration_minutes * 60)
        )
        
        self.access_control.add_rule(rule)
        print(f"Temporarily blocked {{ip_address}} for {{duration_minutes}} minutes")
    
    def get_rate_limit_status(self, user_id: str) -> dict:
        """Get rate limiting status for user"""
        return self.access_control.rate_limiter.get_rate_limit_status(user_id)
    
    async def handle_security_incident(self, incident_type: str, details: dict):
        """Handle security incident"""
        
        ip_address = details.get("ip_address", "unknown")
        user_id = details.get("user_id")
        
        if incident_type == "brute_force_attack":
            # Block IP temporarily
            self.add_temporary_block(ip_address, duration_minutes=120)
            
            # Record security event
            self.access_control._record_security_event(
                "brute_force_detected",
                ThreatLevel.HIGH,
                ip_address,
                user_id,
                "{agent_name}",
                f"Brute force attack detected from {{ip_address}}",
                details
            )
        
        elif incident_type == "suspicious_activity":
            # Increase monitoring
            self.access_control._record_security_event(
                "suspicious_activity",
                ThreatLevel.MEDIUM,
                ip_address,
                user_id,
                "{agent_name}",
                f"Suspicious activity detected: {{details.get('description')}}",
                details
            )
        
        elif incident_type == "data_breach_attempt":
            # Immediate block
            add_ip_to_blacklist(f"{{ip_address}}/32")
            
            self.access_control._record_security_event(
                "data_breach_attempt",
                ThreatLevel.CRITICAL,
                ip_address,
                user_id,
                "{agent_name}",
                f"Data breach attempt detected from {{ip_address}}",
                details
            )

# Example usage:
# access_control = {agent_name.title().replace("_", "")}AccessControlIntegration()
# 
# # Check request security
# allowed, info = await access_control.check_request_security({{
#     "ip_address": "192.168.1.100",
#     "user_agent": "Mozilla/5.0...",
#     "user_id": "user123",
#     "roles": ["user"],
#     "path": "/api/data",
#     "method": "POST"
# }})
# 
# # Monitor security
# security_status = access_control.monitor_security_events()
# rate_status = access_control.get_rate_limit_status("user123")
# 
# # Handle incidents
# await access_control.handle_security_incident("brute_force_attack", {{
#     "ip_address": "10.0.0.100",
#     "failed_attempts": 10,
#     "time_window": 300
# }})
'''
    
    return integration_example

def update_requirements_for_security():
    """Update requirements.txt with security dependencies"""
    requirements_path = Path("requirements.txt")
    
    try:
        if requirements_path.exists():
            with open(requirements_path, 'r') as f:
                content = f.read()
        else:
            content = ""
        
        # Security dependencies
        new_deps = [
            "# WP-10 Security & Authentication Dependencies",
            "cryptography==41.0.7",
            "PyJWT==2.8.0",
            "bcrypt==4.1.2",
            "passlib==1.7.4",
            "python-jose==3.3.0"
        ]
        
        # Add dependencies if not already present
        for dep in new_deps:
            dep_name = dep.split('==')[0].replace("# ", "")
            if dep_name not in content:
                content += f"\n{dep}"
        
        with open(requirements_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Updated requirements.txt with security dependencies")
        return True
    
    except Exception as e:
        print(f"❌ Error updating requirements.txt: {e}")
        return False

def main():
    print("🚀 WP-10: SECURITY & AUTHENTICATION MIGRATION")
    print("=" * 55)
    
    # Update requirements first
    update_requirements_for_security()
    
    # Find security candidates
    agent_files = find_security_candidates()
    print(f"📁 Found {len(agent_files)} agent files to analyze")
    
    # Analyze security needs
    analysis_results = []
    for agent_file in agent_files:
        result = analyze_security_needs(agent_file)
        analysis_results.append(result)
    
    # Sort by security score (higher = more critical)
    analysis_results.sort(key=lambda x: x.get('security_score', 0), reverse=True)
    
    # Filter candidates
    critical_priority = [r for r in analysis_results if r.get('priority') == 'critical']
    high_priority = [r for r in analysis_results if r.get('priority') == 'high']
    auth_candidates = [r for r in analysis_results if r.get('needs_authentication', False)]
    encryption_candidates = [r for r in analysis_results if r.get('needs_encryption', False)]
    access_control_candidates = [r for r in analysis_results if r.get('needs_access_control', False)]
    rate_limiting_candidates = [r for r in analysis_results if r.get('needs_rate_limiting', False)]
    
    print(f"\n📊 SECURITY ANALYSIS:")
    print(f"🚨 Critical priority: {len(critical_priority)}")
    print(f"⚠️  High priority: {len(high_priority)}")
    print(f"🔐 Authentication candidates: {len(auth_candidates)}")
    print(f"🔒 Encryption candidates: {len(encryption_candidates)}")
    print(f"🛡️  Access control candidates: {len(access_control_candidates)}")
    print(f"⏱️  Rate limiting candidates: {len(rate_limiting_candidates)}")
    
    # Calculate vulnerability metrics
    total_vulnerabilities = sum(r.get('vulnerability_count', 0) for r in analysis_results)
    agents_with_vulnerabilities = len([r for r in analysis_results if r.get('vulnerability_count', 0) > 0])
    
    print(f"\n🔍 VULNERABILITY ASSESSMENT:")
    print(f"🚨 Total vulnerabilities found: {total_vulnerabilities}")
    print(f"📊 Agents with vulnerabilities: {agents_with_vulnerabilities}")
    print(f"📈 Average vulnerabilities per agent: {total_vulnerabilities / len(analysis_results):.1f}")
    
    # Show top security risks
    if critical_priority or high_priority:
        print(f"\n🎯 TOP SECURITY RISKS:")
        top_risks = critical_priority + high_priority
        for result in top_risks[:10]:  # Show top 10
            file_path = result['file_path']
            score = result.get('security_score', 0)
            vuln_count = result.get('vulnerability_count', 0)
            print(f"\n📄 {file_path} (Score: {score}, Vulnerabilities: {vuln_count})")
            print(f"   🔐 Authentication: {'✅' if result.get('needs_authentication') else '❌'}")
            print(f"   🔒 Encryption: {'✅' if result.get('needs_encryption') else '❌'}")
            print(f"   🛡️  Access Control: {'✅' if result.get('needs_access_control') else '❌'}")
            print(f"   ⏱️  Rate Limiting: {'✅' if result.get('needs_rate_limiting') else '❌'}")
            print(f"   🎯 Priority: {result.get('priority', 'low')}")
            
            # Show some vulnerabilities
            vulnerabilities = result.get('vulnerabilities', [])
            if vulnerabilities:
                print(f"   🚨 Vulnerabilities:")
                for vuln in vulnerabilities[:3]:  # Show first 3
                    print(f"      - {vuln}")
    
    # Generate integration examples
    examples_dir = Path("docs/security_examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    generated_count = 0
    priority_agents = critical_priority + high_priority
    for result in priority_agents[:15]:  # Top 15 candidates
        file_path = result['file_path']
        agent_name = file_path.stem
        
        # Generate authentication example
        if result.get('needs_authentication'):
            auth_example = generate_authentication_integration(file_path)
            auth_file = examples_dir / f"{agent_name}_authentication.py"
            with open(auth_file, 'w') as f:
                f.write(auth_example)
        
        # Generate encryption example
        if result.get('needs_encryption'):
            encryption_example = generate_encryption_integration(file_path)
            encryption_file = examples_dir / f"{agent_name}_encryption.py"
            with open(encryption_file, 'w') as f:
                f.write(encryption_example)
        
        # Generate access control example
        if result.get('needs_access_control'):
            access_control_example = generate_access_control_integration(file_path)
            access_control_file = examples_dir / f"{agent_name}_access_control.py"
            with open(access_control_file, 'w') as f:
                f.write(access_control_example)
        
        generated_count += 1
    
    print(f"\n✅ WP-10 SECURITY ANALYSIS COMPLETE!")
    print(f"🔐 Authentication candidates: {len(auth_candidates)} agents")
    print(f"🔒 Encryption candidates: {len(encryption_candidates)} agents")
    print(f"🛡️  Access control candidates: {len(access_control_candidates)} agents")
    print(f"⏱️  Rate limiting candidates: {len(rate_limiting_candidates)} agents")
    print(f"📝 Generated examples: {generated_count} agents")
    
    print(f"\n🚀 Security Benefits:")
    print(f"🔐 Strong authentication with JWT, API keys, and HMAC")
    print(f"🔒 Advanced encryption for data at rest and in transit")
    print(f"🛡️  Comprehensive access control and authorization")
    print(f"⏱️  Rate limiting and DDoS protection")
    print(f"🔍 Security monitoring and threat detection")
    print(f"📊 Audit trails and compliance support")
    
    print(f"\n🚀 Next Steps:")
    print(f"1. Security framework implemented in common/security/")
    print(f"2. Integration examples: docs/security_examples/")
    print(f"3. Use: from common.security.authentication import get_security_manager")
    print(f"4. Use: from common.security.encryption import encrypt_data, get_secrets_manager")
    print(f"5. Use: from common.security.access_control import protect_endpoint")
    
    print(f"\n⚠️  CRITICAL SECURITY RECOMMENDATIONS:")
    print(f"1. Deploy authentication to {len(critical_priority)} critical priority agents IMMEDIATELY")
    print(f"2. Implement encryption for {len(encryption_candidates)} agents handling sensitive data")
    print(f"3. Address {total_vulnerabilities} identified vulnerabilities")
    print(f"4. Setup monitoring for {agents_with_vulnerabilities} vulnerable agents")

if __name__ == "__main__":
    main() 