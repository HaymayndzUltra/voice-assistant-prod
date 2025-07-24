#!/usr/bin/env python3
"""
Agent Ready Signal System
------------------------
Allows agents to report when they're truly ready for service
Addresses Background Agent finding: agents start but don't register ready state
"""

import os
import redis
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class AgentReadySignal:
    """Manages agent ready state in Redis for health checks"""
    
    def __init__(self, agent_name: str, redis_host: str = None):
        self.agent_name = agent_name
        self.redis_host = redis_host or os.getenv('REDIS_HOST', 'redis')
        self.redis_client = None
        self._connect_redis()
    
    def _connect_redis(self):
        """Connect to Redis with retry logic"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=6379,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {self.redis_host}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
    
    def set_ready(self, details: Optional[dict] = None):
        """Mark agent as ready"""
        if not self.redis_client:
            logger.warning("Redis not available, cannot set ready signal")
            return False
        
        try:
            key = f"agent:ready:{self.agent_name}"
            self.redis_client.set(key, "1", ex=300)  # Expire after 5 minutes
            
            # Store additional details if provided
            if details:
                details_key = f"agent:details:{self.agent_name}"
                self.redis_client.hset(details_key, mapping=details)
                self.redis_client.expire(details_key, 300)
            
            logger.info(f"Agent {self.agent_name} marked as ready")
            return True
        except Exception as e:
            logger.error(f"Failed to set ready signal: {e}")
            return False
    
    def set_not_ready(self, reason: str = "shutting down"):
        """Mark agent as not ready"""
        if not self.redis_client:
            return False
        
        try:
            key = f"agent:ready:{self.agent_name}"
            self.redis_client.delete(key)
            
            # Store reason
            reason_key = f"agent:not_ready:{self.agent_name}"
            self.redis_client.set(reason_key, reason, ex=60)
            
            logger.info(f"Agent {self.agent_name} marked as not ready: {reason}")
            return True
        except Exception as e:
            logger.error(f"Failed to set not ready signal: {e}")
            return False
    
    def is_ready(self) -> bool:
        """Check if agent is ready"""
        if not self.redis_client:
            return False
        
        try:
            key = f"agent:ready:{self.agent_name}"
            return self.redis_client.get(key) == "1"
        except Exception as e:
            logger.error(f"Failed to check ready signal: {e}")
            return False
    
    def heartbeat(self):
        """Send heartbeat to keep ready signal alive"""
        if not self.redis_client:
            return False
        
        try:
            key = f"agent:ready:{self.agent_name}"
            if self.redis_client.exists(key):
                self.redis_client.expire(key, 300)  # Reset expiration
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")
            return False
    
    def get_all_ready_agents(self):
        """Get list of all ready agents"""
        if not self.redis_client:
            return []
        
        try:
            keys = self.redis_client.keys("agent:ready:*")
            return [key.replace("agent:ready:", "") for key in keys]
        except Exception as e:
            logger.error(f"Failed to get ready agents: {e}")
            return []

# Convenience function for agents to use
def mark_agent_ready(agent_name: str, details: Optional[dict] = None):
    """Convenience function for agents to mark themselves as ready"""
    signal = AgentReadySignal(agent_name)
    return signal.set_ready(details)

def mark_agent_not_ready(agent_name: str, reason: str = "shutting down"):
    """Convenience function for agents to mark themselves as not ready"""
    signal = AgentReadySignal(agent_name)
    return signal.set_not_ready(reason) 