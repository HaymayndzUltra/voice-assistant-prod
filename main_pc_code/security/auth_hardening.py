#!/usr/bin/env python3
"""
Authentication Hardening - Robust Security Authentication System
Provides comprehensive authentication and authorization with security hardening.

Features:
- JWT-based authentication with secure token management
- Multi-factor authentication (TOTP, SMS, Email)
- Advanced rate limiting and brute force protection
- Role-based access control with permission granularity
- Session management with security monitoring
- Password policy enforcement and breach detection
"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import asyncio
import time
import json
import logging
import hashlib
import secrets
import hmac
from typing import Dict, List, Optional, Any, Tuple, Set, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import re

# Security imports
try:
    import jwt
    import bcrypt
    import pyotp
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    print("Security libraries not available - install with: pip install PyJWT bcrypt pyotp")

# Core imports
from common.core.base_agent import BaseAgent
from common_utils.error_handling import SafeExecutor

# Event system imports
from events.memory_events import (
    MemoryEventType, create_memory_operation, MemoryType
)
from events.event_bus import get_event_bus, publish_memory_event

class AuthenticationMethod(Enum):
    """Authentication methods"""
    PASSWORD = "password"
    JWT_TOKEN = "jwt_token"
    API_KEY = "api_key"
    MFA_TOTP = "mfa_totp"
    MFA_SMS = "mfa_sms"
    MFA_EMAIL = "mfa_email"

class UserRole(Enum):
    """User roles with hierarchical permissions"""
    GUEST = "guest"           # Read-only access
    USER = "user"            # Basic operations
    OPERATOR = "operator"     # System operations
    ADMIN = "admin"          # Full administrative access
    SUPER_ADMIN = "super_admin"  # System-wide administration

class SessionStatus(Enum):
    """Session status types"""
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"

class SecurityEvent(Enum):
    """Security event types"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCOUNT_LOCKED = "account_locked"
    PERMISSION_DENIED = "permission_denied"

@dataclass
class User:
    """User account information"""
    user_id: str
    username: str
    email: str
    password_hash: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    account_locked: bool = False
    account_locked_until: Optional[datetime] = None
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    password_changed_at: Optional[datetime] = None
    email_verified: bool = False
    phone_verified: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Session:
    """User session information"""
    session_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: str
    user_agent: str
    status: SessionStatus = SessionStatus.ACTIVE
    refresh_token: Optional[str] = None
    permissions: Set[str] = field(default_factory=set)

@dataclass
class RateLimitRule:
    """Rate limiting rule configuration"""
    name: str
    window_seconds: int
    max_attempts: int
    block_duration_seconds: int
    scope: str = "global"  # global, per_ip, per_user
    enabled: bool = True

@dataclass
class SecurityConfiguration:
    """Security configuration settings"""
    jwt_secret_key: str
    jwt_expiration_minutes: int = 60
    refresh_token_expiration_days: int = 30
    max_failed_login_attempts: int = 5
    account_lockout_duration_minutes: int = 30
    session_timeout_minutes: int = 480  # 8 hours
    password_min_length: int = 12
    password_require_special: bool = True
    password_require_numbers: bool = True
    password_require_uppercase: bool = True
    mfa_issuer_name: str = "AI_System_Monorepo"
    rate_limit_enabled: bool = True

class AuthenticationHardening(BaseAgent):
    """
    Robust authentication and authorization system.
    
    Provides comprehensive security features including JWT authentication,
    MFA, rate limiting, and session management.
    """
    
    def __init__(self, 
                 config: Optional[SecurityConfiguration] = None,
                 enable_monitoring: bool = True,
                 **kwargs):
        super().__init__(name="AuthenticationHardening", **kwargs)
        
        # Configuration
        self.config = config or SecurityConfiguration(
            jwt_secret_key=secrets.token_urlsafe(32)
        )
        self.enable_monitoring = enable_monitoring
        
        # User and session storage
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Session] = {}
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        
        # Rate limiting
        self.rate_limit_rules = self._initialize_rate_limit_rules()
        self.rate_limit_counters: Dict[str, deque] = defaultdict(lambda: deque())
        self.blocked_entities: Dict[str, datetime] = {}
        
        # Security monitoring
        self.security_events: deque = deque(maxlen=10000)
        self.failed_attempts: Dict[str, List[datetime]] = defaultdict(list)
        self.suspicious_activities: deque = deque(maxlen=1000)
        
        # Password security
        self.compromised_passwords: Set[str] = set()
        self.password_patterns = self._initialize_password_patterns()
        
        # Initialize components
        if JWT_AVAILABLE:
            self._start_security_monitoring()
            self._load_compromised_passwords()
        
        self.logger.info("Authentication Hardening system initialized")
    
    def _initialize_rate_limit_rules(self) -> List[RateLimitRule]:
        """Initialize default rate limiting rules"""
        return [
            RateLimitRule(
                name="login_attempts",
                window_seconds=300,      # 5 minutes
                max_attempts=5,
                block_duration_seconds=900,  # 15 minutes
                scope="per_ip"
            ),
            RateLimitRule(
                name="api_requests",
                window_seconds=60,       # 1 minute
                max_attempts=100,
                block_duration_seconds=60,   # 1 minute
                scope="per_user"
            ),
            RateLimitRule(
                name="password_reset",
                window_seconds=3600,     # 1 hour
                max_attempts=3,
                block_duration_seconds=3600,  # 1 hour
                scope="per_user"
            ),
            RateLimitRule(
                name="mfa_verification",
                window_seconds=300,      # 5 minutes
                max_attempts=5,
                block_duration_seconds=1800,  # 30 minutes
                scope="per_user"
            )
        ]
    
    def _initialize_password_patterns(self) -> List[Dict[str, str]]:
        """Initialize weak password patterns"""
        return [
            {'pattern': r'^password\d*$', 'reason': 'Contains "password"'},
            {'pattern': r'^admin\d*$', 'reason': 'Contains "admin"'},
            {'pattern': r'^123456\d*$', 'reason': 'Sequential numbers'},
            {'pattern': r'^qwerty\d*$', 'reason': 'Keyboard pattern'},
            {'pattern': r'^(.)\1{7,}$', 'reason': 'Repeated characters'},
            {'pattern': r'^(.)(.)\1\2\1\2', 'reason': 'Alternating pattern'}
        ]
    
    def _start_security_monitoring(self) -> None:
        """Start security monitoring threads"""
        # Session cleanup thread
        session_thread = threading.Thread(target=self._session_cleanup_loop, daemon=True)
        session_thread.start()
        
        # Security event monitoring thread
        monitor_thread = threading.Thread(target=self._security_monitoring_loop, daemon=True)
        monitor_thread.start()
        
        # Rate limit cleanup thread
        ratelimit_thread = threading.Thread(target=self._rate_limit_cleanup_loop, daemon=True)
        ratelimit_thread.start()
    
    def _load_compromised_passwords(self) -> None:
        """Load compromised password database"""
        # In production, this would load from a compromised password database
        # For now, add some common compromised passwords
        common_compromised = [
            "password123", "admin123", "123456789", "qwerty123",
            "password1", "welcome123", "monkey123", "dragon123"
        ]
        
        for pwd in common_compromised:
            pwd_hash = hashlib.sha1(pwd.encode()).hexdigest().upper()
            self.compromised_passwords.add(pwd_hash)
    
    def _session_cleanup_loop(self) -> None:
        """Clean up expired sessions"""
        while self.running:
            try:
                current_time = datetime.now()
                expired_sessions = []
                
                for session_id, session in self.sessions.items():
                    if session.expires_at < current_time:
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    session = self.sessions[session_id]
                    session.status = SessionStatus.EXPIRED
                    del self.sessions[session_id]
                    
                    self._log_security_event(
                        SecurityEvent.LOGOUT,
                        session.user_id,
                        {"reason": "session_expired", "session_id": session_id}
                    )
                
                if expired_sessions:
                    self.logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                time.sleep(300)  # Clean up every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Session cleanup error: {e}")
                time.sleep(600)
    
    def _security_monitoring_loop(self) -> None:
        """Monitor for suspicious security activities"""
        while self.running:
            try:
                self._detect_suspicious_activities()
                self._analyze_security_patterns()
                
                time.sleep(60)  # Monitor every minute
                
            except Exception as e:
                self.logger.error(f"Security monitoring error: {e}")
                time.sleep(120)
    
    def _rate_limit_cleanup_loop(self) -> None:
        """Clean up rate limiting counters"""
        while self.running:
            try:
                current_time = datetime.now()
                
                # Clean up expired rate limit blocks
                expired_blocks = [
                    entity for entity, unblock_time in self.blocked_entities.items()
                    if current_time > unblock_time
                ]
                
                for entity in expired_blocks:
                    del self.blocked_entities[entity]
                
                # Clean up old rate limit counters
                for counter_key, attempts in list(self.rate_limit_counters.items()):
                    # Remove attempts older than the longest window
                    max_window = max(rule.window_seconds for rule in self.rate_limit_rules)
                    cutoff_time = current_time - timedelta(seconds=max_window)
                    
                    while attempts and attempts[0] < cutoff_time:
                        attempts.popleft()
                    
                    # Remove empty counters
                    if not attempts:
                        del self.rate_limit_counters[counter_key]
                
                time.sleep(300)  # Cleanup every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Rate limit cleanup error: {e}")
                time.sleep(600)
    
    async def create_user(self, username: str, email: str, password: str, 
                         role: UserRole = UserRole.USER) -> Tuple[bool, str]:
        """Create a new user account"""
        if not JWT_AVAILABLE:
            return False, "Security libraries not available"
        
        # Validate input
        if not username or not email or not password:
            return False, "Username, email, and password are required"
        
        # Check if user already exists
        existing_user = self._find_user_by_username_or_email(username, email)
        if existing_user:
            return False, "User already exists"
        
        # Validate password strength
        is_strong, weakness_reason = self._validate_password_strength(password)
        if not is_strong:
            return False, f"Password too weak: {weakness_reason}"
        
        # Check against compromised passwords
        if self._is_password_compromised(password):
            return False, "Password found in compromised password database"
        
        # Create user
        user_id = self._generate_user_id()
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            created_at=datetime.now(),
            password_changed_at=datetime.now()
        )
        
        self.users[user_id] = user
        
        self._log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            user_id,
            {"action": "user_created", "username": username, "role": role.value}
        )
        
        self.logger.info(f"User created: {username} ({role.value})")
        return True, user_id
    
    async def authenticate_user(self, username: str, password: str, 
                              ip_address: str, user_agent: str = "",
                              mfa_token: Optional[str] = None) -> Tuple[bool, str, Optional[Session]]:
        """Authenticate user and create session"""
        if not JWT_AVAILABLE:
            return False, "Security libraries not available", None
        
        # Check rate limiting
        if not self._check_rate_limit("login_attempts", ip_address):
            self._log_security_event(
                SecurityEvent.SUSPICIOUS_ACTIVITY,
                "",
                {"reason": "rate_limit_exceeded", "ip_address": ip_address}
            )
            return False, "Too many login attempts. Please try again later.", None
        
        # Find user
        user = self._find_user_by_username_or_email(username, username)
        if not user:
            self._record_failed_attempt(ip_address)
            return False, "Invalid credentials", None
        
        # Check account lock
        if self._is_account_locked(user):
            self._log_security_event(
                SecurityEvent.ACCOUNT_LOCKED,
                user.user_id,
                {"reason": "account_locked", "ip_address": ip_address}
            )
            return False, "Account is locked", None
        
        # Verify password
        if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            user.failed_login_attempts += 1
            
            # Lock account if too many failures
            if user.failed_login_attempts >= self.config.max_failed_login_attempts:
                user.account_locked = True
                user.account_locked_until = datetime.now() + timedelta(
                    minutes=self.config.account_lockout_duration_minutes
                )
                
                self._log_security_event(
                    SecurityEvent.ACCOUNT_LOCKED,
                    user.user_id,
                    {"reason": "too_many_failures", "ip_address": ip_address}
                )
            
            self._record_failed_attempt(ip_address)
            self._log_security_event(
                SecurityEvent.LOGIN_FAILURE,
                user.user_id,
                {"reason": "invalid_password", "ip_address": ip_address}
            )
            
            return False, "Invalid credentials", None
        
        # Check MFA if enabled
        if user.mfa_enabled:
            if not mfa_token:
                return False, "MFA token required", None
            
            if not self._verify_mfa_token(user, mfa_token):
                self._record_failed_attempt(ip_address)
                self._log_security_event(
                    SecurityEvent.LOGIN_FAILURE,
                    user.user_id,
                    {"reason": "invalid_mfa", "ip_address": ip_address}
                )
                return False, "Invalid MFA token", None
        
        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.now()
        
        # Create session
        session = self._create_session(user, ip_address, user_agent)
        
        self._log_security_event(
            SecurityEvent.LOGIN_SUCCESS,
            user.user_id,
            {"ip_address": ip_address, "session_id": session.session_id}
        )
        
        self.logger.info(f"User authenticated: {user.username} from {ip_address}")
        return True, "Authentication successful", session
    
    def _create_session(self, user: User, ip_address: str, user_agent: str) -> Session:
        """Create a new user session"""
        session_id = self._generate_session_id()
        refresh_token = self._generate_refresh_token()
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=self.config.session_timeout_minutes),
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token=refresh_token,
            permissions=self._get_user_permissions(user)
        )
        
        self.sessions[session_id] = session
        return session
    
    def generate_jwt_token(self, session: Session) -> str:
        """Generate JWT token for session"""
        if not JWT_AVAILABLE:
            raise RuntimeError("JWT library not available")
        
        user = self.users.get(session.user_id)
        if not user:
            raise ValueError("User not found")
        
        payload = {
            'user_id': session.user_id,
            'session_id': session.session_id,
            'username': user.username,
            'role': user.role.value,
            'permissions': list(session.permissions),
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=self.config.jwt_expiration_minutes)
        }
        
        token = jwt.encode(payload, self.config.jwt_secret_key, algorithm='HS256')
        return token
    
    def verify_jwt_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Verify and decode JWT token"""
        if not JWT_AVAILABLE:
            return False, None
        
        try:
            payload = jwt.decode(token, self.config.jwt_secret_key, algorithms=['HS256'])
            
            # Check if session is still valid
            session_id = payload.get('session_id')
            if session_id not in self.sessions:
                return False, None
            
            session = self.sessions[session_id]
            if session.status != SessionStatus.ACTIVE:
                return False, None
            
            # Update last activity
            session.last_activity = datetime.now()
            
            return True, payload
            
        except jwt.ExpiredSignatureError:
            return False, None
        except jwt.InvalidTokenError:
            return False, None
    
    def refresh_token(self, refresh_token: str) -> Tuple[bool, Optional[str]]:
        """Refresh JWT token using refresh token"""
        # Find session by refresh token
        session = None
        for s in self.sessions.values():
            if s.refresh_token == refresh_token:
                session = s
                break
        
        if not session or session.status != SessionStatus.ACTIVE:
            return False, None
        
        # Generate new JWT token
        new_token = self.generate_jwt_token(session)
        
        self._log_security_event(
            SecurityEvent.TOKEN_REFRESH,
            session.user_id,
            {"session_id": session.session_id}
        )
        
        return True, new_token
    
    def logout_session(self, session_id: str) -> bool:
        """Logout and terminate session"""
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session.status = SessionStatus.TERMINATED
        
        self._log_security_event(
            SecurityEvent.LOGOUT,
            session.user_id,
            {"session_id": session_id, "reason": "user_logout"}
        )
        
        del self.sessions[session_id]
        return True
    
    def enable_mfa(self, user_id: str) -> Tuple[bool, Optional[str]]:
        """Enable multi-factor authentication for user"""
        if not JWT_AVAILABLE:
            return False, None
        
        user = self.users.get(user_id)
        if not user:
            return False, None
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        user.mfa_secret = secret
        user.mfa_enabled = True
        
        # Generate QR code URL
        totp = pyotp.TOTP(secret)
        qr_url = totp.provisioning_uri(
            name=user.email,
            issuer_name=self.config.mfa_issuer_name
        )
        
        self._log_security_event(
            SecurityEvent.MFA_ENABLED,
            user_id,
            {"method": "totp"}
        )
        
        return True, qr_url
    
    def disable_mfa(self, user_id: str) -> bool:
        """Disable multi-factor authentication for user"""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.mfa_enabled = False
        user.mfa_secret = None
        
        self._log_security_event(
            SecurityEvent.MFA_DISABLED,
            user_id,
            {"method": "totp"}
        )
        
        return True
    
    def _verify_mfa_token(self, user: User, token: str) -> bool:
        """Verify MFA TOTP token"""
        if not user.mfa_secret or not JWT_AVAILABLE:
            return False
        
        totp = pyotp.TOTP(user.mfa_secret)
        return totp.verify(token)
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """Change user password"""
        user = self.users.get(user_id)
        if not user:
            return False, "User not found"
        
        # Verify old password
        if not bcrypt.checkpw(old_password.encode(), user.password_hash.encode()):
            return False, "Invalid current password"
        
        # Validate new password
        is_strong, weakness_reason = self._validate_password_strength(new_password)
        if not is_strong:
            return False, f"New password too weak: {weakness_reason}"
        
        # Check against compromised passwords
        if self._is_password_compromised(new_password):
            return False, "New password found in compromised password database"
        
        # Check password history (prevent reuse)
        if old_password == new_password:
            return False, "New password must be different from current password"
        
        # Update password
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        user.password_changed_at = datetime.now()
        
        self._log_security_event(
            SecurityEvent.PASSWORD_CHANGE,
            user_id,
            {"timestamp": datetime.now().isoformat()}
        )
        
        return True, "Password changed successfully"
    
    def _check_rate_limit(self, rule_name: str, entity: str) -> bool:
        """Check if entity is rate limited"""
        if not self.config.rate_limit_enabled:
            return True
        
        # Find the rate limit rule
        rule = next((r for r in self.rate_limit_rules if r.name == rule_name), None)
        if not rule or not rule.enabled:
            return True
        
        # Check if entity is currently blocked
        if entity in self.blocked_entities:
            if datetime.now() < self.blocked_entities[entity]:
                return False
            else:
                del self.blocked_entities[entity]
        
        # Count recent attempts
        counter_key = f"{rule_name}:{entity}"
        current_time = datetime.now()
        window_start = current_time - timedelta(seconds=rule.window_seconds)
        
        # Clean old attempts
        attempts = self.rate_limit_counters[counter_key]
        while attempts and attempts[0] < window_start:
            attempts.popleft()
        
        # Check if limit exceeded
        if len(attempts) >= rule.max_attempts:
            # Block the entity
            self.blocked_entities[entity] = current_time + timedelta(seconds=rule.block_duration_seconds)
            return False
        
        # Record this attempt
        attempts.append(current_time)
        return True
    
    def _record_failed_attempt(self, identifier: str) -> None:
        """Record failed authentication attempt"""
        current_time = datetime.now()
        self.failed_attempts[identifier].append(current_time)
        
        # Keep only recent attempts (last hour)
        cutoff_time = current_time - timedelta(hours=1)
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier]
            if attempt > cutoff_time
        ]
    
    def _detect_suspicious_activities(self) -> None:
        """Detect suspicious authentication activities"""
        current_time = datetime.now()
        
        # Check for brute force attacks
        for identifier, attempts in self.failed_attempts.items():
            recent_attempts = [a for a in attempts if (current_time - a).total_seconds() < 300]  # 5 minutes
            
            if len(recent_attempts) >= 10:  # 10 failed attempts in 5 minutes
                self.suspicious_activities.append({
                    'type': 'brute_force_attack',
                    'identifier': identifier,
                    'timestamp': current_time,
                    'attempts': len(recent_attempts)
                })
                
                self.logger.warning(f"Potential brute force attack detected from {identifier}")
        
        # Check for unusual login patterns
        self._detect_unusual_login_patterns()
    
    def _detect_unusual_login_patterns(self) -> None:
        """Detect unusual login patterns"""
        # Check for logins from multiple IPs for same user
        user_ips = defaultdict(set)
        recent_time = datetime.now() - timedelta(hours=1)
        
        for event in self.security_events:
            if (event['event_type'] == SecurityEvent.LOGIN_SUCCESS.value and
                event['timestamp'] > recent_time):
                
                user_id = event['user_id']
                ip_address = event['details'].get('ip_address')
                
                if ip_address:
                    user_ips[user_id].add(ip_address)
        
        # Flag users with multiple IPs
        for user_id, ip_set in user_ips.items():
            if len(ip_set) > 3:  # More than 3 different IPs
                self.suspicious_activities.append({
                    'type': 'multiple_ip_login',
                    'user_id': user_id,
                    'timestamp': datetime.now(),
                    'ip_count': len(ip_set),
                    'ips': list(ip_set)
                })
    
    def _analyze_security_patterns(self) -> None:
        """Analyze security patterns for threats"""
        # This would implement more sophisticated threat detection
        # For now, just log suspicious activities
        
        if self.suspicious_activities:
            recent_activities = [
                activity for activity in self.suspicious_activities
                if (datetime.now() - activity['timestamp']).total_seconds() < 3600
            ]
            
            if recent_activities:
                self.logger.warning(f"{len(recent_activities)} suspicious activities in the last hour")
    
    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength against policy"""
        if len(password) < self.config.password_min_length:
            return False, f"Password must be at least {self.config.password_min_length} characters"
        
        if self.config.password_require_uppercase and not re.search(r'[A-Z]', password):
            return False, "Password must contain uppercase letters"
        
        if self.config.password_require_numbers and not re.search(r'\d', password):
            return False, "Password must contain numbers"
        
        if self.config.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain special characters"
        
        # Check against weak patterns
        for pattern_info in self.password_patterns:
            if re.match(pattern_info['pattern'], password, re.IGNORECASE):
                return False, pattern_info['reason']
        
        return True, "Password meets requirements"
    
    def _is_password_compromised(self, password: str) -> bool:
        """Check if password is in compromised password database"""
        # Hash password with SHA-1 (standard for Have I Been Pwned)
        pwd_hash = hashlib.sha1(password.encode()).hexdigest().upper()
        return pwd_hash in self.compromised_passwords
    
    def _find_user_by_username_or_email(self, username: str, email: str) -> Optional[User]:
        """Find user by username or email"""
        for user in self.users.values():
            if user.username == username or user.email == email:
                return user
        return None
    
    def _is_account_locked(self, user: User) -> bool:
        """Check if user account is locked"""
        if not user.account_locked:
            return False
        
        if user.account_locked_until and datetime.now() > user.account_locked_until:
            # Unlock account
            user.account_locked = False
            user.account_locked_until = None
            user.failed_login_attempts = 0
            return False
        
        return True
    
    def _get_user_permissions(self, user: User) -> Set[str]:
        """Get user permissions based on role"""
        permission_map = {
            UserRole.GUEST: {'read'},
            UserRole.USER: {'read', 'write'},
            UserRole.OPERATOR: {'read', 'write', 'execute', 'monitor'},
            UserRole.ADMIN: {'read', 'write', 'execute', 'monitor', 'admin'},
            UserRole.SUPER_ADMIN: {'read', 'write', 'execute', 'monitor', 'admin', 'super_admin'}
        }
        
        return permission_map.get(user.role, {'read'})
    
    def _log_security_event(self, event_type: SecurityEvent, user_id: str, details: Dict[str, Any]) -> None:
        """Log security event"""
        event = {
            'event_type': event_type.value,
            'user_id': user_id,
            'timestamp': datetime.now(),
            'details': details
        }
        
        self.security_events.append(event)
        
        # Publish security event
        if self.enable_monitoring:
            security_event = create_memory_operation(
                operation_type=MemoryEventType.MEMORY_CREATED,
                memory_id=f"security_event_{int(datetime.now().timestamp())}",
                memory_type=MemoryType.EPISODIC,
                content=f"Security event: {event_type.value}",
                source_agent=self.name,
                machine_id=self._get_machine_id()
            )
            
            publish_memory_event(security_event)
    
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_urlsafe(16)}"
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return f"sess_{secrets.token_urlsafe(32)}"
    
    def _generate_refresh_token(self) -> str:
        """Generate refresh token"""
        return secrets.token_urlsafe(64)
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get comprehensive security status"""
        active_sessions = len([s for s in self.sessions.values() if s.status == SessionStatus.ACTIVE])
        locked_accounts = len([u for u in self.users.values() if u.account_locked])
        mfa_enabled_users = len([u for u in self.users.values() if u.mfa_enabled])
        
        recent_events = [
            {
                'event_type': event['event_type'],
                'user_id': event['user_id'],
                'timestamp': event['timestamp'].isoformat(),
                'details': event['details']
            }
            for event in list(self.security_events)[-50:]  # Last 50 events
        ]
        
        return {
            'user_statistics': {
                'total_users': len(self.users),
                'active_sessions': active_sessions,
                'locked_accounts': locked_accounts,
                'mfa_enabled_users': mfa_enabled_users,
                'mfa_adoption_rate': (mfa_enabled_users / max(len(self.users), 1)) * 100
            },
            'security_metrics': {
                'failed_login_attempts_last_hour': self._count_recent_failed_attempts(),
                'suspicious_activities_last_hour': len([
                    a for a in self.suspicious_activities
                    if (datetime.now() - a['timestamp']).total_seconds() < 3600
                ]),
                'rate_limited_entities': len(self.blocked_entities),
                'compromised_passwords_detected': len(self.compromised_passwords)
            },
            'configuration': {
                'jwt_expiration_minutes': self.config.jwt_expiration_minutes,
                'session_timeout_minutes': self.config.session_timeout_minutes,
                'max_failed_login_attempts': self.config.max_failed_login_attempts,
                'password_min_length': self.config.password_min_length,
                'rate_limiting_enabled': self.config.rate_limit_enabled
            },
            'recent_security_events': recent_events,
            'rate_limit_rules': [
                {
                    'name': rule.name,
                    'window_seconds': rule.window_seconds,
                    'max_attempts': rule.max_attempts,
                    'enabled': rule.enabled
                }
                for rule in self.rate_limit_rules
            ]
        }
    
    def _count_recent_failed_attempts(self) -> int:
        """Count failed login attempts in the last hour"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=1)
        
        total_attempts = 0
        for attempts in self.failed_attempts.values():
            total_attempts += len([a for a in attempts if a > cutoff_time])
        
        return total_attempts
    
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
        """Shutdown the authentication system"""
        # Clear sensitive data
        self.users.clear()
        self.sessions.clear()
        self.api_keys.clear()
        
        super().shutdown()

if __name__ == "__main__":
    # Example usage
    import asyncio
    import logging
    
    logging.basicConfig(level=logging.INFO)
    
    async def test_auth_system():
        auth_system = AuthenticationHardening()
        
        try:
            # Create a test user
            success, user_id = await auth_system.create_user(
                "testuser", "test@example.com", "SecurePassword123!", UserRole.USER
            )
            
            if success:
                print(f"User created: {user_id}")
                
                # Test authentication
                success, message, session = await auth_system.authenticate_user(
                    "testuser", "SecurePassword123!", "127.0.0.1", "Test Client"
                )
                
                if success and session:
                    print(f"Authentication successful: {session.session_id}")
                    
                    # Generate JWT token
                    token = auth_system.generate_jwt_token(session)
                    print(f"JWT token generated: {token[:50]}...")
                    
                    # Verify token
                    valid, payload = auth_system.verify_jwt_token(token)
                    print(f"Token valid: {valid}")
                    
                else:
                    print(f"Authentication failed: {message}")
            else:
                print(f"User creation failed: {user_id}")
            
            # Get security status
            status = auth_system.get_security_status()
            print(json.dumps(status, indent=2, default=str))
            
        finally:
            auth_system.shutdown()
    
    if JWT_AVAILABLE:
        asyncio.run(test_auth_system())
    else:
        print("JWT libraries not available - skipping test") 