
# WP-10 Authentication Integration for translation_service
# Add comprehensive authentication and authorization

from common.security.authentication import (
    get_security_manager, SecurityContext, AuthenticationMethod,
    require_auth, ResourceType, PermissionLevel
)

class TranslationServiceAuthenticationIntegration:
    """Authentication integration for translation_service"""
    
    def __init__(self):
        self.security_manager = get_security_manager()
        
        # Create agent-specific API key
        key_id, api_key = self.security_manager.create_api_key(
            name="translation_service_service_key",
            permissions={
                "agent:read", "agent:write", "agent:execute",
                "api:read", "api:write", "data:read", "data:write"
            },
            rate_limit=100  # requests per minute
        )
        
        # Store API key securely (in production, use secrets manager)
        self.api_key = api_key
        print(f"Generated API key for translation_service: {key_id}")
    
    async def authenticate_request(self, request_headers: dict) -> SecurityContext:
        """Authenticate incoming request"""
        
        # Try JWT authentication
        auth_header = request_headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            context = await self.security_manager.authenticate(
                AuthenticationMethod.JWT,
                {"token": token}
            )
            if context:
                return context
        
        # Try API key authentication
        api_key = request_headers.get("X-API-Key")
        if api_key:
            context = await self.security_manager.authenticate(
                AuthenticationMethod.API_KEY,
                {"api_key": api_key},
                request_info={
                    "ip_address": request_headers.get("X-Real-IP", "unknown"),
                    "user_agent": request_headers.get("User-Agent", "unknown")
                }
            )
            if context:
                return context
        
        # Try HMAC authentication for system-to-system
        signature = request_headers.get("X-Signature")
        timestamp = request_headers.get("X-Timestamp")
        if signature and timestamp:
            context = await self.security_manager.authenticate(
                AuthenticationMethod.HMAC,
                {
                    "method": "POST",
                    "path": "/api/translation_service",
                    "body": "",  # Request body
                    "timestamp": timestamp,
                    "signature": signature
                }
            )
            if context:
                return context
        
        return None
    
    @require_auth(resource=ResourceType.AGENT, action=PermissionLevel.READ)
    async def get_agent_status(self, security_context: SecurityContext):
        """Get agent status - requires read permission"""
        return {
            "agent_id": "translation_service",
            "status": "running",
            "authenticated_user": security_context.user_id,
            "permissions": list(security_context.permissions)
        }
    
    @require_auth(resource=ResourceType.AGENT, action=PermissionLevel.EXECUTE)
    async def execute_operation(self, operation: str, data: dict, 
                               security_context: SecurityContext):
        """Execute operation - requires execute permission"""
        
        # Log security context
        print(f"User {security_context.user_id} executing {operation}")
        
        # Check specific operation permissions
        if operation == "sensitive_operation":
            if not security_context.has_role("admin"):
                raise PermissionError("Admin role required for sensitive operations")
        
        # Perform operation
        result = await self.perform_operation(operation, data)
        
        return {
            "operation": operation,
            "result": result,
            "executed_by": security_context.user_id,
            "timestamp": time.time()
        }
    
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
        print(f"Data update by {security_context.user_id}: {data_id}")
        
        # Perform update
        result = await self.update_database(data_id, data)
        
        return result
    
    def generate_user_token(self, user_id: str, roles: set = None) -> str:
        """Generate authentication token for user"""
        
        # Default roles for this agent
        default_roles = {"viewer", "operator"}
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
            name=f"{service_name}_service",
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
            path=f"/api/translation_service",
            body=json.dumps(request_data, sort_keys=True),
            timestamp=timestamp,
            received_signature=signature
        )

# Example usage:
# auth_integration = TranslationServiceAuthenticationIntegration()
# 
# # In your request handler:
# security_context = await auth_integration.authenticate_request(request.headers)
# if not security_context:
#     raise HTTPException(401, "Authentication required")
# 
# # Use protected methods:
# status = await auth_integration.get_agent_status(security_context=security_context)
# result = await auth_integration.execute_operation("process_data", data, security_context=security_context)
