from common.core.base_agent import BaseAgent
"""Authentication middleware with JWT and trust scoring."""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from functools import wraps

import jwt
from fastapi import HTTPException, Security, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

logger = logging.getLogger("memory_hub.auth")


class AuthConfig(BaseModel):
    """Authentication configuration."""
    jwt_secret: str = ""  # Will be populated from SecretManager or environment
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    require_auth: bool = True
    trusted_agents: List[str] = ["CoreOrchestrator", "PlanningOrchestrator"]
    trust_threshold: float = 0.7


class User(BaseModel):
    """User model."""
    user_id: str
    username: str
    roles: List[str] = []
    agent_name: Optional[str] = None
    trust_score: float = 0.0
    metadata: Dict[str, Any] = {}


class TrustScore:
    """Trust scoring system for agents and users."""
    
    def __init__(self, storage_manager):

        super().__init__(*args, **kwargs)        self.storage = storage_manager
        self.base_scores = {
            "CoreOrchestrator": 1.0,
            "PlanningOrchestrator": 1.0,
            "MemoryHub": 1.0,
            "user": 0.5,
            "guest": 0.1
        }
    
    async def get_trust_score(self, user_id: str, agent_name: Optional[str] = None) -> float:
        """Get trust score for user/agent."""
        try:
            # Check Redis cache first
            cache_key = f"trust_score:{user_id}"
            cached_score = await self.storage.redis_get("auth", "trust", cache_key)
            
            if cached_score:
                return float(cached_score)
            
            # Calculate base score
            if agent_name and agent_name in self.base_scores:
                base_score = self.base_scores[agent_name]
            else:
                base_score = self.base_scores.get("user", 0.5)
            
            # Get historical interactions from storage
            interaction_data = await self._get_interaction_history(user_id)
            
            # Calculate dynamic trust score
            trust_score = self._calculate_trust_score(base_score, interaction_data)
            
            # Cache the result for 1 hour
            await self.storage.redis_set("auth", "trust", cache_key, str(trust_score), expire=3600)
            
            return trust_score
        
        except Exception as e:
            logger.error(f"Error calculating trust score for {user_id}: {e}")
            return 0.1  # Default low trust
    
    async def _get_interaction_history(self, user_id: str) -> Dict[str, Any]:
        """Get interaction history from storage."""
        try:
            # Get recent interactions from Redis
            interactions_key = f"interactions:{user_id}"
            interactions_data = await self.storage.redis_get("auth", "trust", interactions_key)
            
            if interactions_data:
                return json.loads(interactions_data)
            
            return {
                "successful_requests": 0,
                "failed_requests": 0,
                "recent_activity": [],
                "violations": 0
            }
        
        except Exception as e:
            logger.error(f"Error getting interaction history for {user_id}: {e}")
            return {}
    
    def _calculate_trust_score(self, base_score: float, interaction_data: Dict[str, Any]) -> float:
        """Calculate trust score based on interaction history."""
        try:
            successful = interaction_data.get("successful_requests", 0)
            failed = interaction_data.get("failed_requests", 0)
            violations = interaction_data.get("violations", 0)
            
            total_requests = successful + failed
            
            if total_requests == 0:
                return base_score
            
            # Success ratio factor
            success_ratio = successful / total_requests
            success_factor = min(success_ratio * 1.2, 1.0)  # Cap at 1.0
            
            # Violation penalty
            violation_penalty = min(violations * 0.1, 0.5)  # Cap penalty at 0.5
            
            # Activity bonus (small bonus for active users)
            activity_bonus = min(total_requests / 1000, 0.1)  # Cap at 0.1
            
            # Calculate final score
            final_score = base_score * success_factor - violation_penalty + activity_bonus
            
            # Ensure score is between 0 and 1
            return max(0.0, min(1.0, final_score))
        
        except Exception as e:
            logger.error(f"Error calculating trust score: {e}")
            return base_score * 0.5  # Reduced base score on error
    
    async def record_interaction(self, user_id: str, success: bool, violation: bool = False):
        """Record user interaction for trust scoring."""
        try:
            interactions_key = f"interactions:{user_id}"
            interaction_data = await self._get_interaction_history(user_id)
            
            # Update counters
            if success:
                interaction_data["successful_requests"] = interaction_data.get("successful_requests", 0) + 1
            else:
                interaction_data["failed_requests"] = interaction_data.get("failed_requests", 0) + 1
            
            if violation:
                interaction_data["violations"] = interaction_data.get("violations", 0) + 1
            
            # Add to recent activity (keep last 100 interactions)
            recent_activity = interaction_data.get("recent_activity", [])
            recent_activity.append({
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "violation": violation
            })
            
            # Keep only last 100 interactions
            interaction_data["recent_activity"] = recent_activity[-100:]
            
            # Store updated data
            await self.storage.redis_set(
                "auth", "trust", interactions_key, 
                json.dumps(interaction_data), 
                expire=86400 * 30  # 30 days
            )
            
            # Invalidate trust score cache
            cache_key = f"trust_score:{user_id}"
            await self.storage.redis_delete("auth", "trust", cache_key)
        
        except Exception as e:
            logger.error(f"Error recording interaction for {user_id}: {e}")


class AuthMiddleware:
    """JWT Authentication middleware with trust scoring."""
    
    def __init__(self, config: AuthConfig, storage_manager):

        super().__init__(*args, **kwargs)        self.config = config
        self.storage = storage_manager
        self.trust_scorer = TrustScore(storage_manager)
        self.security = HTTPBearer(auto_error=False)
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token."""
        payload = {
            "user_id": user.user_id,
            "username": user.username,
            "roles": user.roles,
            "agent_name": user.agent_name,
            "trust_score": user.trust_score,
            "exp": datetime.utcnow() + timedelta(hours=self.config.jwt_expire_hours),
            "iat": datetime.utcnow()
        }
        
        return jwt.encode(payload, self.config.jwt_secret, algorithm=self.config.jwt_algorithm)
    
    async def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user."""
        try:
            payload = jwt.decode(token, self.config.jwt_secret, algorithms=[self.config.jwt_algorithm])
            
            # Get fresh trust score
            trust_score = await self.trust_scorer.get_trust_score(
                payload["user_id"], 
                payload.get("agent_name")
            )
            
            user = User(
                user_id=payload["user_id"],
                username=payload["username"],
                roles=payload.get("roles", []),
                agent_name=payload.get("agent_name"),
                trust_score=trust_score,
                metadata=payload.get("metadata", {})
            )
            
            return user
        
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying token: {e}")
            return None
    
    async def authenticate_request(self, request: Request, 
                                 credentials: Optional[HTTPAuthorizationCredentials] = None) -> Optional[User]:
        """Authenticate incoming request."""
        if not self.config.require_auth:
            # Create guest user when auth is disabled
            return User(
                user_id="guest",
                username="guest",
                roles=["guest"],
                trust_score=self.trust_scorer.base_scores["guest"]
            )
        
        if not credentials:
            return None
        
        user = await self.verify_token(credentials.credentials)
        
        if user:
            # Record successful authentication
            await self.trust_scorer.record_interaction(user.user_id, success=True)
        else:
            # Record failed authentication
            client_ip = request.client.host if request.client else "unknown"
            await self.trust_scorer.record_interaction(
                f"failed_auth:{client_ip}", 
                success=False, 
                violation=True
            )
        
        return user
    
    async def require_auth(self, min_trust: float = 0.0, 
                         required_roles: List[str] = None) -> User:
        """Dependency for requiring authentication."""
        async def _require_auth(request: Request, 
                              credentials: Optional[HTTPAuthorizationCredentials] = Security(self.security)) -> User:
            
            user = await self.authenticate_request(request, credentials)
            
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # Check trust score
            if user.trust_score < min_trust:
                await self.trust_scorer.record_interaction(user.user_id, success=False, violation=True)
                raise HTTPException(
                    status_code=403, 
                    detail=f"Insufficient trust score: {user.trust_score:.2f} < {min_trust:.2f}"
                )
            
            # Check roles
            if required_roles:
                if not any(role in user.roles for role in required_roles):
                    await self.trust_scorer.record_interaction(user.user_id, success=False, violation=True)
                    raise HTTPException(
                        status_code=403, 
                        detail=f"Required roles: {required_roles}, user roles: {user.roles}"
                    )
            
            return user
        
        return _require_auth
    
    async def create_agent_token(self, agent_name: str) -> str:
        """Create token for trusted agents."""
        trust_score = await self.trust_scorer.get_trust_score("system", agent_name)
        
        user = User(
            user_id=f"agent:{agent_name}",
            username=agent_name,
            roles=["agent", "system"],
            agent_name=agent_name,
            trust_score=trust_score
        )
        
        return self.create_access_token(user)
    
    async def validate_agent_access(self, agent_name: str, required_trust: float = 0.7) -> bool:
        """Validate if agent has sufficient access."""
        if agent_name in self.config.trusted_agents:
            return True
        
        trust_score = await self.trust_scorer.get_trust_score("system", agent_name)
        return trust_score >= required_trust


# Global auth instance (will be initialized with storage manager)
auth_middleware: Optional[AuthMiddleware] = None


def init_auth_middleware(config: AuthConfig, storage_manager) -> AuthMiddleware:
    """Initialize global auth middleware."""
    global auth_middleware
    auth_middleware = AuthMiddleware(config, storage_manager)
    return auth_middleware


async def get_current_user(request: Request, 
                         credentials: Optional[HTTPAuthorizationCredentials] = Security(HTTPBearer(auto_error=False))) -> Optional[User]:
    """FastAPI dependency for getting current user."""
    if not auth_middleware:
        raise HTTPException(status_code=500, detail="Auth middleware not initialized")
    
    return await auth_middleware.authenticate_request(request, credentials)


def require_auth(min_trust: float = 0.0, required_roles: List[str] = None):
    """FastAPI dependency factory for requiring authentication."""
    if not auth_middleware:
        raise HTTPException(status_code=500, detail="Auth middleware not initialized")
    
    return auth_middleware.require_auth(min_trust, required_roles)


def require_high_trust():
    """Shortcut for high trust requirements."""
    return require_auth(min_trust=0.8)


def require_agent_access():
    """Shortcut for agent-only access."""
    return require_auth(min_trust=0.7, required_roles=["agent", "system"]) 