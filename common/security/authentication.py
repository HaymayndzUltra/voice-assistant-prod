"""
WP-10 Security & Authentication
Comprehensive authentication, authorization, and security framework for distributed AI agents
"""

import asyncio
import time
import hashlib
import hmac
import jwt
import secrets
import bcrypt
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)

class AuthenticationMethod(Enum):
    """Authentication methods"""
    JWT = "jwt"
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    MUTUAL_TLS = "mutual_tls"
    HMAC = "hmac"

class PermissionLevel(Enum):
    """Permission levels"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    SYSTEM = "system"

class ResourceType(Enum):
    """Resource types for authorization"""
    AGENT = "agent"
    API = "api"
    DATA = "data"
    CONFIG = "config"
    LOGS = "logs"
    METRICS = "metrics"
    SYSTEM = "system"

@dataclass
class SecurityContext:
    """Security context for authenticated entities"""
    user_id: str
    agent_id: Optional[str] = None
    session_id: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    permissions: Set[str] = field(default_factory=set)
    roles: Set[str] = field(default_factory=set)
    authentication_method: AuthenticationMethod = AuthenticationMethod.JWT
    expires_at: Optional[datetime] = None
    issued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if security context is expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def has_permission(self, resource: str, action: str) -> bool:
        """Check if context has specific permission"""
        permission = f"{resource}:{action}"
        return permission in self.permissions or "system:*" in self.permissions
    
    def has_role(self, role: str) -> bool:
        """Check if context has specific role"""
        return role in self.roles
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "permissions": list(self.permissions),
            "roles": list(self.roles),
            "authentication_method": self.authentication_method.value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "issued_at": self.issued_at.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": self.metadata
        }

@dataclass
class ApiKey:
    """API key for authentication"""
    key_id: str
    key_hash: str
    name: str
    permissions: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_used: Optional[datetime] = None
    usage_count: int = 0
    rate_limit: Optional[int] = None  # requests per minute
    enabled: bool = True
    
    def is_valid(self) -> bool:
        """Check if API key is valid"""
        if not self.enabled:
            return False
        
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        
        return True
    
    def verify_key(self, raw_key: str) -> bool:
        """Verify raw key against stored hash"""
        return bcrypt.checkpw(raw_key.encode('utf-8'), self.key_hash.encode('utf-8'))

class JWTManager:
    """JWT token management"""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = "ai_system"
    
    def generate_token(self, security_context: SecurityContext, 
                      expires_in: timedelta = timedelta(hours=24)) -> str:
        """Generate JWT token"""
        payload = {
            "sub": security_context.user_id,
            "agent_id": security_context.agent_id,
            "session_id": security_context.session_id,
            "permissions": list(security_context.permissions),
            "roles": list(security_context.roles),
            "iat": int(security_context.issued_at.timestamp()),
            "exp": int((security_context.issued_at + expires_in).timestamp()),
            "iss": self.issuer,
            "ip": security_context.ip_address,
            "metadata": security_context.metadata
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[SecurityContext]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check expiration
            if payload.get("exp") and time.time() > payload["exp"]:
                return None
            
            # Create security context
            context = SecurityContext(
                user_id=payload["sub"],
                agent_id=payload.get("agent_id"),
                session_id=payload.get("session_id", secrets.token_urlsafe(32)),
                permissions=set(payload.get("permissions", [])),
                roles=set(payload.get("roles", [])),
                authentication_method=AuthenticationMethod.JWT,
                issued_at=datetime.fromtimestamp(payload.get("iat", time.time()), timezone.utc),
                expires_at=datetime.fromtimestamp(payload["exp"], timezone.utc) if payload.get("exp") else None,
                ip_address=payload.get("ip"),
                metadata=payload.get("metadata", {})
            )
            
            return context
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
        except Exception as e:
            logger.error(f"JWT verification error: {e}")
            return None

class HMACValidator:
    """HMAC signature validation for API requests"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key.encode('utf-8')
    
    def generate_signature(self, method: str, path: str, body: str, timestamp: str) -> str:
        """Generate HMAC signature"""
        message = f"{method}|{path}|{body}|{timestamp}"
        signature = hmac.new(
            self.secret_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def verify_signature(self, method: str, path: str, body: str, 
                        timestamp: str, received_signature: str) -> bool:
        """Verify HMAC signature"""
        # Check timestamp (prevent replay attacks)
        try:
            request_time = float(timestamp)
            current_time = time.time()
            
            # Allow 5 minutes of clock skew
            if abs(current_time - request_time) > 300:
                return False
        except ValueError:
            return False
        
        # Verify signature
        expected_signature = self.generate_signature(method, path, body, timestamp)
        return hmac.compare_digest(expected_signature, received_signature)

class PermissionManager:
    """Manage permissions and authorization"""
    
    def __init__(self):
        self._permissions: Dict[str, Set[str]] = {}
        self._roles: Dict[str, Set[str]] = {}
        self._role_hierarchy: Dict[str, Set[str]] = {}
        
        # Setup default permissions and roles
        self._setup_default_permissions()
    
    def _setup_default_permissions(self):
        """Setup default permissions and roles"""
        # Default roles
        self.define_role("viewer", {
            "agent:read", "api:read", "data:read", "logs:read", "metrics:read"
        })
        
        self.define_role("operator", {
            "agent:read", "agent:write", "api:read", "api:write",
            "data:read", "data:write", "logs:read", "metrics:read"
        })
        
        self.define_role("admin", {
            "agent:*", "api:*", "data:*", "config:*", 
            "logs:*", "metrics:*"
        })
        
        self.define_role("system", {"system:*"})
        
        # Role hierarchy
        self.set_role_hierarchy("admin", {"operator", "viewer"})
        self.set_role_hierarchy("operator", {"viewer"})
    
    def define_role(self, role_name: str, permissions: Set[str]):
        """Define a role with permissions"""
        self._roles[role_name] = permissions
    
    def set_role_hierarchy(self, parent_role: str, child_roles: Set[str]):
        """Set role hierarchy (parent inherits child permissions)"""
        self._role_hierarchy[parent_role] = child_roles
    
    def get_effective_permissions(self, roles: Set[str]) -> Set[str]:
        """Get effective permissions for given roles"""
        permissions = set()
        
        for role in roles:
            # Add direct permissions
            permissions.update(self._roles.get(role, set()))
            
            # Add inherited permissions
            child_roles = self._role_hierarchy.get(role, set())
            for child_role in child_roles:
                permissions.update(self._roles.get(child_role, set()))
        
        return permissions
    
    def check_permission(self, context: SecurityContext, 
                        resource: ResourceType, action: PermissionLevel) -> bool:
        """Check if security context has permission"""
        # System permissions override everything
        if "system:*" in context.permissions:
            return True
        
        # Check direct permission
        permission = f"{resource.value}:{action.value}"
        if permission in context.permissions:
            return True
        
        # Check wildcard permission
        wildcard = f"{resource.value}:*"
        if wildcard in context.permissions:
            return True
        
        # Check role-based permissions
        effective_permissions = self.get_effective_permissions(context.roles)
        return permission in effective_permissions or wildcard in effective_permissions

class SessionManager:
    """Manage user sessions"""
    
    def __init__(self, session_timeout: timedelta = timedelta(hours=24)):
        self._sessions: Dict[str, SecurityContext] = {}
        self.session_timeout = session_timeout
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_expired_sessions())
    
    def create_session(self, user_id: str, **kwargs) -> SecurityContext:
        """Create new session"""
        context = SecurityContext(
            user_id=user_id,
            expires_at=datetime.now(timezone.utc) + self.session_timeout,
            **kwargs
        )
        
        self._sessions[context.session_id] = context
        return context
    
    def get_session(self, session_id: str) -> Optional[SecurityContext]:
        """Get session by ID"""
        context = self._sessions.get(session_id)
        
        if context and context.is_expired():
            self.revoke_session(session_id)
            return None
        
        return context
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoke session"""
        return self._sessions.pop(session_id, None) is not None
    
    def refresh_session(self, session_id: str) -> bool:
        """Refresh session expiry"""
        context = self._sessions.get(session_id)
        if context:
            context.expires_at = datetime.now(timezone.utc) + self.session_timeout
            return True
        return False
    
    async def _cleanup_expired_sessions(self):
        """Background task to cleanup expired sessions"""
        while True:
            try:
                expired_sessions = [
                    session_id for session_id, context in self._sessions.items()
                    if context.is_expired()
                ]
                
                for session_id in expired_sessions:
                    self.revoke_session(session_id)
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Session cleanup error: {e}")
                await asyncio.sleep(300)

class ApiKeyManager:
    """Manage API keys"""
    
    def __init__(self):
        self._api_keys: Dict[str, ApiKey] = {}
        self._rate_limits: Dict[str, List[float]] = {}  # key_id -> timestamps
    
    def generate_api_key(self, name: str, permissions: Set[str] = None,
                        expires_in: Optional[timedelta] = None,
                        rate_limit: Optional[int] = None) -> tuple[str, str]:
        """Generate new API key"""
        # Generate key
        key_id = f"ak_{secrets.token_urlsafe(16)}"
        raw_key = secrets.token_urlsafe(32)
        
        # Hash key
        key_hash = bcrypt.hashpw(raw_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create API key record
        api_key = ApiKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions or set(),
            expires_at=datetime.now(timezone.utc) + expires_in if expires_in else None,
            rate_limit=rate_limit
        )
        
        self._api_keys[key_id] = api_key
        
        # Return key_id and raw key
        return key_id, f"{key_id}.{raw_key}"
    
    def verify_api_key(self, api_key_string: str) -> Optional[SecurityContext]:
        """Verify API key and return security context"""
        try:
            # Parse key string
            parts = api_key_string.split('.', 1)
            if len(parts) != 2:
                return None
            
            key_id, raw_key = parts
            
            # Get API key record
            api_key = self._api_keys.get(key_id)
            if not api_key or not api_key.is_valid():
                return None
            
            # Verify key
            if not api_key.verify_key(raw_key):
                return None
            
            # Check rate limit
            if api_key.rate_limit and not self._check_rate_limit(key_id, api_key.rate_limit):
                return None
            
            # Update usage
            api_key.last_used = datetime.now(timezone.utc)
            api_key.usage_count += 1
            
            # Create security context
            context = SecurityContext(
                user_id=f"api_key:{key_id}",
                session_id=f"api:{key_id}",
                permissions=api_key.permissions,
                authentication_method=AuthenticationMethod.API_KEY,
                expires_at=api_key.expires_at,
                metadata={"api_key_name": api_key.name}
            )
            
            return context
            
        except Exception as e:
            logger.error(f"API key verification error: {e}")
            return None
    
    def _check_rate_limit(self, key_id: str, rate_limit: int) -> bool:
        """Check if API key is within rate limit"""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        # Get existing timestamps
        timestamps = self._rate_limits.get(key_id, [])
        
        # Remove old timestamps
        timestamps = [ts for ts in timestamps if ts > window_start]
        
        # Check if under limit
        if len(timestamps) >= rate_limit:
            return False
        
        # Add current timestamp
        timestamps.append(current_time)
        self._rate_limits[key_id] = timestamps
        
        return True
    
    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke API key"""
        api_key = self._api_keys.get(key_id)
        if api_key:
            api_key.enabled = False
            return True
        return False
    
    def list_api_keys(self, user_filter: str = None) -> List[Dict[str, Any]]:
        """List API keys"""
        keys = []
        for api_key in self._api_keys.values():
            if user_filter and user_filter not in api_key.name:
                continue
            
            keys.append({
                "key_id": api_key.key_id,
                "name": api_key.name,
                "permissions": list(api_key.permissions),
                "created_at": api_key.created_at.isoformat(),
                "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
                "last_used": api_key.last_used.isoformat() if api_key.last_used else None,
                "usage_count": api_key.usage_count,
                "enabled": api_key.enabled
            })
        
        return keys

class SecurityManager:
    """Central security management"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        
        # Initialize components
        self.jwt_manager = JWTManager(self.secret_key)
        self.hmac_validator = HMACValidator(self.secret_key)
        self.permission_manager = PermissionManager()
        self.session_manager = SessionManager()
        self.api_key_manager = ApiKeyManager()
        
        # Security settings
        self.require_https = True
        self.max_login_attempts = 5
        self.login_timeout = timedelta(minutes=15)
        
        # Failed login tracking
        self._failed_logins: Dict[str, List[datetime]] = {}
        
        logger.info("Security manager initialized")
    
    async def authenticate(self, method: AuthenticationMethod, 
                          credentials: Dict[str, Any],
                          request_info: Dict[str, Any] = None) -> Optional[SecurityContext]:
        """Authenticate using specified method"""
        
        if method == AuthenticationMethod.JWT:
            token = credentials.get("token")
            if token:
                return self.jwt_manager.verify_token(token)
        
        elif method == AuthenticationMethod.API_KEY:
            api_key = credentials.get("api_key")
            if api_key:
                context = self.api_key_manager.verify_api_key(api_key)
                if context and request_info:
                    context.ip_address = request_info.get("ip_address")
                    context.user_agent = request_info.get("user_agent")
                return context
        
        elif method == AuthenticationMethod.HMAC:
            required_fields = ["method", "path", "body", "timestamp", "signature"]
            if all(field in credentials for field in required_fields):
                if self.hmac_validator.verify_signature(
                    credentials["method"],
                    credentials["path"], 
                    credentials["body"],
                    credentials["timestamp"],
                    credentials["signature"]
                ):
                    # Create system context for HMAC
                    return SecurityContext(
                        user_id="system:hmac",
                        permissions={"system:*"},
                        authentication_method=AuthenticationMethod.HMAC
                    )
        
        return None
    
    def authorize(self, context: SecurityContext, 
                 resource: ResourceType, action: PermissionLevel) -> bool:
        """Authorize action on resource"""
        if context.is_expired():
            return False
        
        return self.permission_manager.check_permission(context, resource, action)
    
    def generate_token(self, user_id: str, roles: Set[str] = None,
                      permissions: Set[str] = None,
                      expires_in: timedelta = timedelta(hours=24)) -> str:
        """Generate authentication token"""
        
        # Get effective permissions
        effective_permissions = permissions or set()
        if roles:
            effective_permissions.update(
                self.permission_manager.get_effective_permissions(roles)
            )
        
        context = SecurityContext(
            user_id=user_id,
            roles=roles or set(),
            permissions=effective_permissions
        )
        
        return self.jwt_manager.generate_token(context, expires_in)
    
    def create_api_key(self, name: str, permissions: Set[str] = None,
                      expires_in: Optional[timedelta] = None,
                      rate_limit: Optional[int] = None) -> tuple[str, str]:
        """Create new API key"""
        return self.api_key_manager.generate_api_key(
            name, permissions, expires_in, rate_limit
        )
    
    def check_rate_limit(self, user_id: str, max_requests: int = 100,
                        window_minutes: int = 1) -> bool:
        """Check if user is within rate limit"""
        current_time = datetime.now(timezone.utc)
        window_start = current_time - timedelta(minutes=window_minutes)
        
        # Get failed login attempts
        attempts = self._failed_logins.get(user_id, [])
        
        # Remove old attempts
        attempts = [attempt for attempt in attempts if attempt > window_start]
        
        # Check limit
        return len(attempts) < max_requests
    
    def record_failed_login(self, user_id: str):
        """Record failed login attempt"""
        current_time = datetime.now(timezone.utc)
        
        if user_id not in self._failed_logins:
            self._failed_logins[user_id] = []
        
        self._failed_logins[user_id].append(current_time)
    
    def is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked due to failed attempts"""
        if not self.check_rate_limit(user_id, self.max_login_attempts, 15):
            return True
        return False

# Global security manager
_security_manager: Optional[SecurityManager] = None

def get_security_manager() -> SecurityManager:
    """Get global security manager"""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager

def setup_security(secret_key: str = None, **config) -> SecurityManager:
    """Setup security system"""
    global _security_manager
    _security_manager = SecurityManager(secret_key)
    
    # Apply configuration
    for key, value in config.items():
        if hasattr(_security_manager, key):
            setattr(_security_manager, key, value)
    
    return _security_manager

# Decorator for securing functions
def require_auth(resource: ResourceType = ResourceType.API, 
                action: PermissionLevel = PermissionLevel.READ,
                methods: List[AuthenticationMethod] = None):
    """Decorator to require authentication and authorization"""
    
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract security context from kwargs or request
            context = kwargs.get("security_context")
            
            if not context:
                raise PermissionError("Authentication required")
            
            # Check authorization
            security_manager = get_security_manager()
            if not security_manager.authorize(context, resource, action):
                raise PermissionError(f"Insufficient permissions for {resource.value}:{action.value}")
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Extract security context from kwargs
            context = kwargs.get("security_context")
            
            if not context:
                raise PermissionError("Authentication required")
            
            # Check authorization
            security_manager = get_security_manager()
            if not security_manager.authorize(context, resource, action):
                raise PermissionError(f"Insufficient permissions for {resource.value}:{action.value}")
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Convenience functions
async def authenticate_request(method: AuthenticationMethod,
                             credentials: Dict[str, Any],
                             request_info: Dict[str, Any] = None) -> Optional[SecurityContext]:
    """Authenticate request"""
    security_manager = get_security_manager()
    return await security_manager.authenticate(method, credentials, request_info)

def generate_system_token(agent_id: str = None) -> str:
    """Generate system-level token"""
    security_manager = get_security_manager()
    return security_manager.generate_token(
        user_id=f"system:{agent_id}" if agent_id else "system",
        permissions={"system:*"}
    ) 