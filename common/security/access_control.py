"""
WP-10 Access Control & Rate Limiting
Advanced access control, rate limiting, and security monitoring for AI agents
"""

import asyncio
import time
import threading
from typing import Dict, Any, Optional, List, Set, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import ipaddress
import logging

logger = logging.getLogger(__name__)

class RateLimitType(Enum):
    """Types of rate limiting"""
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    BANDWIDTH_PER_SECOND = "bandwidth_per_second"
    CONCURRENT_CONNECTIONS = "concurrent_connections"

class AccessDecision(Enum):
    """Access control decisions"""
    ALLOW = "allow"
    DENY = "deny"
    CHALLENGE = "challenge"
    THROTTLE = "throttle"

class ThreatLevel(Enum):
    """Security threat levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class RateLimitRule:
    """Rate limiting rule"""
    name: str
    limit_type: RateLimitType
    max_requests: int
    time_window: int  # seconds
    burst_allowance: int = 0
    enabled: bool = True
    
    def __post_init__(self):
        self.request_times: deque = deque()
        self.burst_count = 0
        self.lock = threading.RLock()

@dataclass
class AccessRule:
    """Access control rule"""
    name: str
    priority: int
    conditions: Dict[str, Any]
    action: AccessDecision
    enabled: bool = True
    expires_at: Optional[float] = None
    
    def matches(self, context: Dict[str, Any]) -> bool:
        """Check if rule matches context"""
        for key, expected_value in self.conditions.items():
            actual_value = context.get(key)
            
            if isinstance(expected_value, list):
                if actual_value not in expected_value:
                    return False
            elif isinstance(expected_value, dict):
                if "range" in expected_value:
                    min_val, max_val = expected_value["range"]
                    if not (min_val <= actual_value <= max_val):
                        return False
                elif "regex" in expected_value:
                    import re
                    if not re.match(expected_value["regex"], str(actual_value)):
                        return False
                elif "contains" in expected_value:
                    if expected_value["contains"] not in str(actual_value):
                        return False
            else:
                if actual_value != expected_value:
                    return False
        
        return True
    
    def is_expired(self) -> bool:
        """Check if rule is expired"""
        return self.expires_at is not None and time.time() > self.expires_at

@dataclass
class SecurityEvent:
    """Security monitoring event"""
    event_type: str
    threat_level: ThreatLevel
    source_ip: str
    user_id: Optional[str]
    agent_id: Optional[str]
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_type": self.event_type,
            "threat_level": self.threat_level.value,
            "source_ip": self.source_ip,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }

class IPAccessControl:
    """IP-based access control"""
    
    def __init__(self):
        self.whitelist: Set[ipaddress.IPv4Network] = set()
        self.blacklist: Set[ipaddress.IPv4Network] = set()
        self.geo_restrictions: Dict[str, bool] = {}  # country_code -> allowed
        self.lock = threading.RLock()
    
    def add_to_whitelist(self, ip_range: str):
        """Add IP range to whitelist"""
        with self.lock:
            network = ipaddress.IPv4Network(ip_range, strict=False)
            self.whitelist.add(network)
            logger.info(f"Added to IP whitelist: {ip_range}")
    
    def add_to_blacklist(self, ip_range: str):
        """Add IP range to blacklist"""
        with self.lock:
            network = ipaddress.IPv4Network(ip_range, strict=False)
            self.blacklist.add(network)
            logger.info(f"Added to IP blacklist: {ip_range}")
    
    def remove_from_whitelist(self, ip_range: str):
        """Remove IP range from whitelist"""
        with self.lock:
            network = ipaddress.IPv4Network(ip_range, strict=False)
            self.whitelist.discard(network)
    
    def remove_from_blacklist(self, ip_range: str):
        """Remove IP range from blacklist"""
        with self.lock:
            network = ipaddress.IPv4Network(ip_range, strict=False)
            self.blacklist.discard(network)
    
    def is_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed"""
        try:
            ip = ipaddress.IPv4Address(ip_address)
            
            with self.lock:
                # Check blacklist first
                for network in self.blacklist:
                    if ip in network:
                        return False
                
                # If whitelist exists, IP must be in it
                if self.whitelist:
                    for network in self.whitelist:
                        if ip in network:
                            return True
                    return False
                
                # No whitelist restrictions
                return True
                
        except ipaddress.AddressValueError:
            return False

class RateLimiter:
    """Advanced rate limiting"""
    
    def __init__(self):
        self.rules: Dict[str, RateLimitRule] = {}
        self.user_counters: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(deque))
        self.global_counters: Dict[str, deque] = defaultdict(deque)
        self.lock = threading.RLock()
        
        # Setup default rules
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Setup default rate limiting rules"""
        self.add_rule(RateLimitRule(
            name="api_requests_per_minute",
            limit_type=RateLimitType.REQUESTS_PER_MINUTE,
            max_requests=100,
            time_window=60,
            burst_allowance=20
        ))
        
        self.add_rule(RateLimitRule(
            name="api_requests_per_hour",
            limit_type=RateLimitType.REQUESTS_PER_HOUR,
            max_requests=1000,
            time_window=3600,
            burst_allowance=100
        ))
        
        self.add_rule(RateLimitRule(
            name="auth_attempts_per_minute",
            limit_type=RateLimitType.REQUESTS_PER_MINUTE,
            max_requests=5,
            time_window=60,
            burst_allowance=0
        ))
    
    def add_rule(self, rule: RateLimitRule):
        """Add rate limiting rule"""
        with self.lock:
            self.rules[rule.name] = rule
            logger.info(f"Added rate limit rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove rate limiting rule"""
        with self.lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                logger.info(f"Removed rate limit rule: {rule_name}")
    
    def check_rate_limit(self, user_id: str, rule_name: str, 
                        increment: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is within rate limit"""
        rule = self.rules.get(rule_name)
        if not rule or not rule.enabled:
            return True, {}
        
        current_time = time.time()
        window_start = current_time - rule.time_window
        
        with rule.lock:
            # Get user's request history for this rule
            user_requests = self.user_counters[user_id][rule_name]
            
            # Remove old requests outside time window
            while user_requests and user_requests[0] <= window_start:
                user_requests.popleft()
            
            # Check if within limit
            current_count = len(user_requests)
            allowed = current_count < rule.max_requests
            
            # Check burst allowance
            if not allowed and rule.burst_allowance > 0:
                if rule.burst_count < rule.burst_allowance:
                    allowed = True
                    rule.burst_count += 1
            
            # Increment counter if request is allowed
            if allowed and increment:
                user_requests.append(current_time)
            
            # Calculate retry after
            retry_after = 0
            if not allowed and user_requests:
                oldest_request = user_requests[0]
                retry_after = int(oldest_request + rule.time_window - current_time)
            
            return allowed, {
                "rule_name": rule_name,
                "current_count": current_count,
                "max_requests": rule.max_requests,
                "time_window": rule.time_window,
                "retry_after": retry_after,
                "burst_used": rule.burst_count
            }
    
    def reset_burst_allowance(self, rule_name: str):
        """Reset burst allowance for rule"""
        rule = self.rules.get(rule_name)
        if rule:
            with rule.lock:
                rule.burst_count = 0
    
    def get_rate_limit_status(self, user_id: str) -> Dict[str, Dict[str, Any]]:
        """Get rate limit status for user"""
        status = {}
        
        for rule_name, rule in self.rules.items():
            allowed, info = self.check_rate_limit(user_id, rule_name, increment=False)
            status[rule_name] = {
                "allowed": allowed,
                **info
            }
        
        return status

class AccessControlEngine:
    """Main access control engine"""
    
    def __init__(self):
        self.rules: List[AccessRule] = []
        self.ip_control = IPAccessControl()
        self.rate_limiter = RateLimiter()
        self.security_events: deque = deque(maxlen=10000)
        self.lock = threading.RLock()
        
        # Setup default rules
        self._setup_default_rules()
        
        # Start cleanup task
        asyncio.create_task(self._cleanup_expired_rules())
    
    def _setup_default_rules(self):
        """Setup default access control rules"""
        # Block suspicious user agents
        self.add_rule(AccessRule(
            name="block_suspicious_user_agents",
            priority=100,
            conditions={
                "user_agent": {
                    "regex": r".*(bot|crawler|spider|scraper).*"
                }
            },
            action=AccessDecision.DENY
        ))
        
        # Throttle high-frequency requests
        self.add_rule(AccessRule(
            name="throttle_high_frequency",
            priority=200,
            conditions={
                "request_frequency": {
                    "range": [10, float('inf')]
                }
            },
            action=AccessDecision.THROTTLE
        ))
        
        # Allow admin access
        self.add_rule(AccessRule(
            name="allow_admin_access",
            priority=10,
            conditions={
                "roles": ["admin", "system"]
            },
            action=AccessDecision.ALLOW
        ))
    
    def add_rule(self, rule: AccessRule):
        """Add access control rule"""
        with self.lock:
            self.rules.append(rule)
            # Sort by priority (lower number = higher priority)
            self.rules.sort(key=lambda r: r.priority)
            logger.info(f"Added access rule: {rule.name}")
    
    def remove_rule(self, rule_name: str):
        """Remove access control rule"""
        with self.lock:
            self.rules = [r for r in self.rules if r.name != rule_name]
            logger.info(f"Removed access rule: {rule_name}")
    
    def evaluate_access(self, context: Dict[str, Any]) -> Tuple[AccessDecision, Dict[str, Any]]:
        """Evaluate access request"""
        # Extract key information
        ip_address = context.get("ip_address", "")
        user_id = context.get("user_id", "")
        agent_id = context.get("agent_id", "")
        
        # Check IP access control
        if ip_address and not self.ip_control.is_allowed(ip_address):
            self._record_security_event(
                "ip_blocked",
                ThreatLevel.MEDIUM,
                ip_address,
                user_id,
                agent_id,
                f"IP address {ip_address} is blacklisted"
            )
            return AccessDecision.DENY, {"reason": "IP address not allowed"}
        
        # Check rate limits
        if user_id:
            for rule_name in ["api_requests_per_minute", "api_requests_per_hour"]:
                allowed, rate_info = self.rate_limiter.check_rate_limit(user_id, rule_name)
                if not allowed:
                    self._record_security_event(
                        "rate_limit_exceeded",
                        ThreatLevel.LOW,
                        ip_address,
                        user_id,
                        agent_id,
                        f"Rate limit exceeded for rule: {rule_name}"
                    )
                    return AccessDecision.THROTTLE, {
                        "reason": "Rate limit exceeded",
                        "rate_limit_info": rate_info
                    }
        
        # Evaluate access rules
        with self.lock:
            for rule in self.rules:
                if not rule.enabled or rule.is_expired():
                    continue
                
                if rule.matches(context):
                    if rule.action == AccessDecision.DENY:
                        self._record_security_event(
                            "access_denied",
                            ThreatLevel.MEDIUM,
                            ip_address,
                            user_id,
                            agent_id,
                            f"Access denied by rule: {rule.name}"
                        )
                    
                    return rule.action, {
                        "rule_name": rule.name,
                        "reason": f"Matched rule: {rule.name}"
                    }
        
        # Default allow
        return AccessDecision.ALLOW, {"reason": "No matching rules, default allow"}
    
    def _record_security_event(self, event_type: str, threat_level: ThreatLevel,
                             source_ip: str, user_id: Optional[str],
                             agent_id: Optional[str], description: str,
                             metadata: Dict[str, Any] = None):
        """Record security event"""
        event = SecurityEvent(
            event_type=event_type,
            threat_level=threat_level,
            source_ip=source_ip,
            user_id=user_id,
            agent_id=agent_id,
            description=description,
            metadata=metadata or {}
        )
        
        self.security_events.append(event)
        
        # Log based on threat level
        if threat_level == ThreatLevel.CRITICAL:
            logger.critical(f"SECURITY: {description}")
        elif threat_level == ThreatLevel.HIGH:
            logger.error(f"SECURITY: {description}")
        elif threat_level == ThreatLevel.MEDIUM:
            logger.warning(f"SECURITY: {description}")
        else:
            logger.info(f"SECURITY: {description}")
    
    async def _cleanup_expired_rules(self):
        """Background task to cleanup expired rules"""
        while True:
            try:
                with self.lock:
                    self.rules = [r for r in self.rules if not r.is_expired()]
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Rule cleanup error: {e}")
                await asyncio.sleep(300)
    
    def get_security_events(self, threat_level: ThreatLevel = None,
                           limit: int = 100) -> List[SecurityEvent]:
        """Get recent security events"""
        events = list(self.security_events)
        
        if threat_level:
            events = [e for e in events if e.threat_level == threat_level]
        
        return events[-limit:]
    
    def get_security_summary(self) -> Dict[str, Any]:
        """Get security summary"""
        events = list(self.security_events)
        
        # Count by threat level
        threat_counts = {level: 0 for level in ThreatLevel}
        for event in events:
            threat_counts[event.threat_level] += 1
        
        # Count by event type
        event_type_counts = defaultdict(int)
        for event in events:
            event_type_counts[event.event_type] += 1
        
        # Recent activity (last hour)
        recent_cutoff = time.time() - 3600
        recent_events = [e for e in events if e.timestamp > recent_cutoff]
        
        return {
            "total_events": len(events),
            "recent_events": len(recent_events),
            "threat_level_counts": {level.value: count for level, count in threat_counts.items()},
            "event_type_counts": dict(event_type_counts),
            "active_rules": len([r for r in self.rules if r.enabled and not r.is_expired()]),
            "rate_limit_rules": len(self.rate_limiter.rules)
        }

class SecurityMiddleware:
    """Security middleware for request processing"""
    
    def __init__(self, access_control: AccessControlEngine = None):
        self.access_control = access_control or AccessControlEngine()
    
    async def process_request(self, context: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """Process request through security checks"""
        try:
            decision, info = self.access_control.evaluate_access(context)
            
            if decision == AccessDecision.ALLOW:
                return True, info
            elif decision == AccessDecision.DENY:
                return False, {"error": "Access denied", **info}
            elif decision == AccessDecision.THROTTLE:
                return False, {"error": "Request throttled", **info}
            elif decision == AccessDecision.CHALLENGE:
                return False, {"error": "Authentication challenge required", **info}
            else:
                return False, {"error": "Unknown access decision"}
                
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            return False, {"error": "Security check failed"}

# Global instances
_access_control_engine: Optional[AccessControlEngine] = None
_security_middleware: Optional[SecurityMiddleware] = None

def get_access_control_engine() -> AccessControlEngine:
    """Get global access control engine"""
    global _access_control_engine
    if _access_control_engine is None:
        _access_control_engine = AccessControlEngine()
    return _access_control_engine

def get_security_middleware() -> SecurityMiddleware:
    """Get global security middleware"""
    global _security_middleware
    if _security_middleware is None:
        _security_middleware = SecurityMiddleware()
    return _security_middleware

# Decorator for protecting endpoints
def protect_endpoint(rate_limit_rule: str = "api_requests_per_minute",
                    require_auth: bool = True,
                    allowed_roles: List[str] = None):
    """Decorator to protect endpoints with access control"""
    
    def decorator(func):
        import functools
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract context from request
            request = kwargs.get("request")
            security_context = kwargs.get("security_context")
            
            if not request:
                raise ValueError("Request object required for endpoint protection")
            
            # Build security context
            context = {
                "ip_address": getattr(request, "client", {}).get("host", ""),
                "user_agent": getattr(request, "headers", {}).get("user-agent", ""),
                "user_id": security_context.user_id if security_context else None,
                "agent_id": security_context.agent_id if security_context else None,
                "roles": list(security_context.roles) if security_context else [],
                "permissions": list(security_context.permissions) if security_context else []
            }
            
            # Check authentication
            if require_auth and not security_context:
                raise PermissionError("Authentication required")
            
            # Check roles
            if allowed_roles and security_context:
                if not any(role in security_context.roles for role in allowed_roles):
                    raise PermissionError("Insufficient role permissions")
            
            # Check access control
            middleware = get_security_middleware()
            allowed, info = await middleware.process_request(context)
            
            if not allowed:
                error_msg = info.get("error", "Access denied")
                raise PermissionError(error_msg)
            
            return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Simplified sync version
            security_context = kwargs.get("security_context")
            
            if require_auth and not security_context:
                raise PermissionError("Authentication required")
            
            if allowed_roles and security_context:
                if not any(role in security_context.roles for role in allowed_roles):
                    raise PermissionError("Insufficient role permissions")
            
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# Convenience functions
def add_ip_to_blacklist(ip_range: str):
    """Add IP range to blacklist"""
    engine = get_access_control_engine()
    engine.ip_control.add_to_blacklist(ip_range)

def add_ip_to_whitelist(ip_range: str):
    """Add IP range to whitelist"""
    engine = get_access_control_engine()
    engine.ip_control.add_to_whitelist(ip_range)

def check_rate_limit(user_id: str, rule_name: str = "api_requests_per_minute") -> bool:
    """Check if user is within rate limit"""
    engine = get_access_control_engine()
    allowed, _ = engine.rate_limiter.check_rate_limit(user_id, rule_name)
    return allowed 