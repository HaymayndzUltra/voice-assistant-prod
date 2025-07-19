
# WP-10 Access Control Integration for authentication
# Add rate limiting, IP filtering, and security monitoring

from common.security.access_control import (
    get_access_control_engine, get_security_middleware,
    protect_endpoint, AccessDecision, ThreatLevel,
    add_ip_to_blacklist, add_ip_to_whitelist, check_rate_limit
)

class AuthenticationAccessControlIntegration:
    """Access control integration for authentication"""
    
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
            name="authentication_block_bots",
            priority=50,
            conditions={
                "user_agent": {
                    "regex": r".*(bot|crawler|scraper|spider).*"
                }
            },
            action=AccessDecision.DENY
        ))
        
        # Throttle high-frequency requests
        self.access_control.add_rule(AccessRule(
            name="authentication_throttle_high_freq",
            priority=100,
            conditions={
                "request_count_per_minute": {
                    "range": [50, float('inf')]
                }
            },
            action=AccessDecision.THROTTLE
        ))
        
        # Allow admin bypass
        self.access_control.add_rule(AccessRule(
            name="authentication_admin_bypass",
            priority=1,
            conditions={
                "roles": ["admin", "system"]
            },
            action=AccessDecision.ALLOW
        ))
        
        # Block suspicious patterns
        self.access_control.add_rule(AccessRule(
            name="authentication_block_suspicious",
            priority=75,
            conditions={
                "path": {
                    "regex": r".*(admin|config|\.env|\.git|backup).*"
                },
                "roles": []  # No roles (unauthenticated)
            },
            action=AccessDecision.DENY
        ))
    
    def _setup_rate_limits(self):
        """Setup rate limiting rules"""
        from common.security.access_control import RateLimitRule, RateLimitType
        
        # API rate limits
        self.access_control.rate_limiter.add_rule(RateLimitRule(
            name="authentication_api_requests",
            limit_type=RateLimitType.REQUESTS_PER_MINUTE,
            max_requests=60,
            time_window=60,
            burst_allowance=10
        ))
        
        # Authentication attempts
        self.access_control.rate_limiter.add_rule(RateLimitRule(
            name="authentication_auth_attempts",
            limit_type=RateLimitType.REQUESTS_PER_MINUTE,
            max_requests=5,
            time_window=60,
            burst_allowance=0
        ))
        
        # Hourly limits
        self.access_control.rate_limiter.add_rule(RateLimitRule(
            name="authentication_hourly_requests",
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
        rate_limit_rule="authentication_api_requests",
        require_auth=True,
        allowed_roles=["user", "operator", "admin"]
    )
    async def protected_api_endpoint(self, request, security_context):
        """Protected API endpoint with access control"""
        
        # Extract request info
        user_id = security_context.user_id
        ip_address = getattr(request, "client", {}).get("host", "unknown")
        
        print(f"API request from {user_id} ({ip_address})")
        
        # Your endpoint logic here
        return {
            "message": "Access granted",
            "user": user_id,
            "timestamp": time.time()
        }
    
    async def check_request_security(self, request_info: dict) -> tuple:
        """Check request security and return decision"""
        
        # Build context for access control
        context = {
            "ip_address": request_info.get("ip_address", ""),
            "user_agent": request_info.get("user_agent", ""),
            "user_id": request_info.get("user_id"),
            "agent_id": "authentication",
            "roles": request_info.get("roles", []),
            "path": request_info.get("path", ""),
            "method": request_info.get("method", "GET")
        }
        
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
        
        return {
            "summary": summary,
            "recent_threats": len(recent_threats),
            "total_events": len(events),
            "threat_breakdown": {
                level.value: len([e for e in events if e.threat_level == level])
                for level in ThreatLevel
            }
        }
    
    def add_temporary_block(self, ip_address: str, duration_minutes: int = 60):
        """Add temporary IP block"""
        from common.security.access_control import AccessRule
        import time
        
        # Create temporary rule
        rule = AccessRule(
            name=f"temp_block_{ip_address.replace('.', '_')}",
            priority=10,
            conditions={"ip_address": ip_address},
            action=AccessDecision.DENY,
            expires_at=time.time() + (duration_minutes * 60)
        )
        
        self.access_control.add_rule(rule)
        print(f"Temporarily blocked {ip_address} for {duration_minutes} minutes")
    
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
                "authentication",
                f"Brute force attack detected from {ip_address}",
                details
            )
        
        elif incident_type == "suspicious_activity":
            # Increase monitoring
            self.access_control._record_security_event(
                "suspicious_activity",
                ThreatLevel.MEDIUM,
                ip_address,
                user_id,
                "authentication",
                f"Suspicious activity detected: {details.get('description')}",
                details
            )
        
        elif incident_type == "data_breach_attempt":
            # Immediate block
            add_ip_to_blacklist(f"{ip_address}/32")
            
            self.access_control._record_security_event(
                "data_breach_attempt",
                ThreatLevel.CRITICAL,
                ip_address,
                user_id,
                "authentication",
                f"Data breach attempt detected from {ip_address}",
                details
            )

# Example usage:
# access_control = AuthenticationAccessControlIntegration()
# 
# # Check request security
# allowed, info = await access_control.check_request_security({
#     "ip_address": "192.168.1.100",
#     "user_agent": "Mozilla/5.0...",
#     "user_id": "user123",
#     "roles": ["user"],
#     "path": "/api/data",
#     "method": "POST"
# })
# 
# # Monitor security
# security_status = access_control.monitor_security_events()
# rate_status = access_control.get_rate_limit_status("user123")
# 
# # Handle incidents
# await access_control.handle_security_incident("brute_force_attack", {
#     "ip_address": "10.0.0.100",
#     "failed_attempts": 10,
#     "time_window": 300
# })
