#!/usr/bin/env python3
"""
Standardized Health Check System
==============================
Universal health check interface for all agents in the AI system.
Replaces simple socket checks with comprehensive Redis-based ready signals.
"""

import redis
import json
import time
import logging
import asyncio
import socket
from typing import Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class HealthCheck:
    """Health check result"""
    status: HealthStatus
    timestamp: datetime
    checks: Dict[str, bool]
    details: Dict[str, Any]
    error_message: Optional[str] = None

class StandardizedHealthChecker:
    """
    Universal health checker that all agents should inherit from
    """
    
    def __init__(self, agent_name: str, port: int, redis_host: str = "localhost", redis_port: int = 6379):
        self.agent_name = agent_name
        self.port = port
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_client = None
        self.health_data = {}
        
    def connect_redis(self) -> bool:
        """Establish Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis connection failed for {self.agent_name}: {e}")
            return False
    
    def check_port_availability(self) -> bool:
        """Check if agent port is accessible"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(3)
                result = sock.connect_ex(('localhost', self.port))
                return result == 0
        except Exception:
            return False
    
    def check_redis_connectivity(self) -> bool:
        """Check Redis connectivity"""
        try:
            if not self.redis_client:
                return self.connect_redis()
            self.redis_client.ping()
            return True
        except Exception:
            return False
    
    def get_agent_ready_signal(self) -> Dict[str, Any]:
        """Get agent ready signal from Redis"""
        try:
            if not self.redis_client:
                return {}
            
            signal_key = f"agent:ready:{self.agent_name}"
            signal_data = self.redis_client.get(signal_key)
            
            if signal_data:
                return json.loads(signal_data)
            return {}
        except Exception as e:
            logger.error(f"Failed to get ready signal for {self.agent_name}: {e}")
            return {}
    
    def set_agent_ready(self, details: Optional[Dict] = None):
        """Mark agent as ready in Redis"""
        try:
            if not self.redis_client:
                if not self.connect_redis():
                    return False
            
            signal_data = {
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "port": self.port,
                "details": details or {}
            }
            
            signal_key = f"agent:ready:{self.agent_name}"
            self.redis_client.setex(
                signal_key, 
                300,  # 5 minute expiry
                json.dumps(signal_data)
            )
            
            logger.info(f"✅ {self.agent_name} marked as ready in Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set ready signal for {self.agent_name}: {e}")
            return False
    
    def set_agent_not_ready(self, reason: str = "shutting down"):
        """Mark agent as not ready in Redis"""
        try:
            if not self.redis_client:
                return False
            
            signal_key = f"agent:ready:{self.agent_name}"
            self.redis_client.delete(signal_key)
            
            # Log shutdown reason
            shutdown_key = f"agent:shutdown:{self.agent_name}"
            shutdown_data = {
                "reason": reason,
                "timestamp": datetime.now().isoformat()
            }
            self.redis_client.setex(shutdown_key, 3600, json.dumps(shutdown_data))
            
            logger.info(f"🛑 {self.agent_name} marked as not ready: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set not ready signal for {self.agent_name}: {e}")
            return False
    
    def perform_health_check(self) -> HealthCheck:
        """Perform comprehensive health check"""
        checks = {}
        details = {}
        error_message = None
        
        try:
            # Check 1: Port availability
            checks["port_accessible"] = self.check_port_availability()
            details["port"] = self.port
            
            # Check 2: Redis connectivity
            checks["redis_connected"] = self.check_redis_connectivity()
            details["redis_host"] = f"{self.redis_host}:{self.redis_port}"
            
            # Check 3: Ready signal
            ready_signal = self.get_agent_ready_signal()
            checks["ready_signal"] = bool(ready_signal)
            details["ready_signal"] = ready_signal
            
            # Check 4: Custom agent checks (override in subclass)
            custom_checks = self.custom_health_checks()
            checks.update(custom_checks)
            
            # Determine overall status
            if all(checks.values()):
                status = HealthStatus.HEALTHY
            elif checks.get("port_accessible", False) and checks.get("redis_connected", False):
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.UNHEALTHY
                
        except Exception as e:
            status = HealthStatus.UNKNOWN
            error_message = str(e)
            logger.error(f"Health check failed for {self.agent_name}: {e}")
        
        return HealthCheck(
            status=status,
            timestamp=datetime.now(),
            checks=checks,
            details=details,
            error_message=error_message
        )
    
    def custom_health_checks(self) -> Dict[str, bool]:
        """Override this method in agent implementations for custom checks"""
        return {}
    
    def start_health_monitoring(self, interval: int = 30):
        """Start background health monitoring"""
        async def monitor():
            while True:
                health = self.perform_health_check()
                
                # Store health data in Redis
                if self.redis_client:
                    health_key = f"agent:health:{self.agent_name}"
                    health_data = asdict(health)
                    health_data["timestamp"] = health.timestamp.isoformat()
                    
                    self.redis_client.setex(
                        health_key,
                        interval * 2,  # Double the interval for expiry
                        json.dumps(health_data, default=str)
                    )
                
                await asyncio.sleep(interval)
        
        # Start monitoring task
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(monitor())
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.create_task(monitor())

# Convenience functions for external health checks
def check_agent_health(agent_name: str, port: int) -> HealthCheck:
    """Quick health check for any agent"""
    checker = StandardizedHealthChecker(agent_name, port)
    return checker.perform_health_check()

def wait_for_agent_ready(agent_name: str, port: int, timeout: int = 60) -> bool:
    """Wait for agent to become ready"""
    checker = StandardizedHealthChecker(agent_name, port)
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        health = checker.perform_health_check()
        if health.status == HealthStatus.HEALTHY:
            return True
        time.sleep(2)
    
    return False

def get_system_health_summary() -> Dict[str, Any]:
    """Get health summary for all agents"""
    try:
        redis_client = redis.Redis(decode_responses=True)
        
        # Get all agent health keys
        health_keys = redis_client.keys("agent:health:*")
        ready_keys = redis_client.keys("agent:ready:*")
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(health_keys),
            "ready_agents": len(ready_keys),
            "agents": {}
        }
        
        for key in health_keys:
            agent_name = key.split(":")[-1]
            health_data = redis_client.get(key)
            if health_data:
                summary["agents"][agent_name] = json.loads(health_data)
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get system health summary: {e}")
        return {"error": str(e), "timestamp": datetime.now().isoformat()} 