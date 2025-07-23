#!/usr/bin/env python3
from __future__ import annotations
"""Service Registry Agent

A minimal, highly-available registry that other agents can query to discover
endpoints. It intentionally keeps zero external dependencies so that it can
start before the rest of the platform.

Implements two core actions:
1. ``register_agent`` – store/overwrite metadata about an agent.
2. ``get_agent_endpoint`` – return host/port (and extras) for a given agent.

Standard health actions (``ping``, ``health``, ``health_check``) are inherited
from :class:`common.core.base_agent.BaseAgent`.

Supports multiple backend storage options:
- In-memory (default): Fast but non-persistent
- Redis: Persistent and supports high-availability
"""

import argparse
# Prefer orjson for performance if available, but gracefully fall back to the
# standard library ``json`` so the agent can run even when the optional
# dependency is not installed inside the Docker image.
try:
    import orjson as _json  # type: ignore
    _dumps = _json.dumps  # returns bytes
    _loads = _json.loads
except ImportError:  # pragma: no cover – orjson is optional
    import json as _json  # noqa: F401 – fallback

    def _dumps(obj):  # type: ignore
        """Mimic orjson.dumps signature but return bytes for consistency."""
        text = _json.dumps(obj, separators=(",", ":"))
        return text.encode("utf-8")

    def _loads(data):  # type: ignore
        if isinstance(data, (bytes, bytearray)):
            data = data.decode("utf-8")
        return _json.loads(data)

# Expose dumps / loads helpers for this module
dumps = _dumps
loads = _loads
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, Protocol, runtime_checkable

from common.core.base_agent import BaseAgent
from common.utils.data_models import AgentRegistration
from common.env_helpers import get_env

# ---------------------------------------------------------------------------
# Configuration defaults
# ---------------------------------------------------------------------------
DEFAULT_PORT = int(os.getenv("SERVICE_REGISTRY_PORT", 7100))
DEFAULT_HEALTH_PORT = int(os.getenv("SERVICE_REGISTRY_HEALTH_PORT", 8100))
DEFAULT_BACKEND = os.getenv("SERVICE_REGISTRY_BACKEND", "memory")
DEFAULT_${SECRET_PLACEHOLDER}6379/0")
DEFAULT_${SECRET_PLACEHOLDER}")

logger = logging.getLogger("ServiceRegistryAgent")


@runtime_checkable
class RegistryBackend(Protocol):
    """Protocol defining the interface for registry backends."""
    
    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data by ID."""
        ...
    
    def set(self, agent_id: str, data: Dict[str, Any]) -> None:
        """Store agent data by ID."""
        ...
    
    def list_agents(self) -> list[str]:
        """List all registered agent IDs."""
        ...
    
    def close(self) -> None:
        """Close any resources."""
        ...


class MemoryBackend:
    """Simple in-memory backend for the service registry."""
    
    def __init__(self) -> None:
        self.registry: Dict[str, Dict[str, Any]] = {}
    
    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data by ID."""
        return self.registry.get(agent_id)
    
    def set(self, agent_id: str, data: Dict[str, Any]) -> None:
        """Store agent data by ID."""
        self.registry[agent_id] = data
    
    def list_agents(self) -> list[str]:
        """List all registered agent IDs."""
        return list(self.registry.keys())
    
    def close(self) -> None:
        """Close any resources."""
        pass


class RedisBackend:
    """Redis-backed storage for the service registry.
    
    Provides persistence and high-availability.
    """
    
    def __init__(self, redis_url: str, prefix: str = DEFAULT_${SECRET_PLACEHOLDER}
        """Initialize Redis backend.
        
        Args:
            redis_url: Redis connection URL (redis://host:port/db)
            prefix: Key prefix for Redis keys
        """
        try:
            import redis
        except ImportError:
            logger.error("Redis package not installed. Install with: pip install redis")
            raise
        
        self.prefix = prefix
        self.redis = redis.from_url(redis_url)
        logger.info("Connected to Redis at %s", redis_url)
    
    def _key(self, agent_id: str) -> str:
        """Get the Redis key for an agent."""
        return f"{self.prefix}{agent_id}"
    
    def get(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data by ID."""
        data = self.redis.get(self._key(agent_id))
        if data:
            try:
                return loads(data)
            except Exception:  # noqa: BLE001 – handle any decode error gracefully
                logger.error("Invalid JSON data for agent %s", agent_id)
        return None
    
    def set(self, agent_id: str, data: Dict[str, Any]) -> None:
        """Store agent data by ID."""
        # Redis expects ``bytes`` or ``str``.  ``dumps`` returns *bytes* for
        # both the orjson and stdlib fallback, so we can send it directly.
        self.redis.set(self._key(agent_id), dumps(data))
    
    def list_agents(self) -> list[str]:
        """List all registered agent IDs."""
        keys = self.redis.keys(f"{self.prefix}*")
        return [key.decode('utf-8').replace(self.prefix, '') for key in keys]
    
    def close(self) -> None:
        """Close Redis connection."""
        self.redis.close()


class ServiceRegistryAgent(BaseAgent):
    """A service registry with configurable backend storage."""

    def __init__(self, backend: str = DEFAULT_BACKEND, redis_url: str = DEFAULT_${SECRET_PLACEHOLDER}
        """Initialize the service registry.
        
        Args:
            backend: Storage backend ('memory' or 'redis')
            redis_url: Redis connection URL if using redis backend
            **kwargs: Additional arguments passed to BaseAgent
        """
        # Initialize backend before BaseAgent starts threads
        if backend == "redis":
            logger.info("Using Redis backend at %s", redis_url)
            self.backend: RegistryBackend = RedisBackend(redis_url)
        else:
            logger.info("Using in-memory backend")
            self.backend = MemoryBackend()

        # Merge default ports with kwargs, but allow kwargs to override.
        port = int(kwargs.pop("port", DEFAULT_PORT))
        health = int(kwargs.pop("health_check_port", DEFAULT_HEALTH_PORT))

        super().__init__(name="ServiceRegistry", port=port, health_check_port=health, **kwargs)

    # ---------------------------------------------------------------------
    # Request handling
    # ---------------------------------------------------------------------
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch incoming requests by *action*.

        Parameters
        ----------
        request : Dict[str, Any]
            JSON-serialised request containing at minimum an ``action`` key.
        """
        action = request.get("action")

        # BaseAgent already handles the canonical health verbs.
        if action in {"ping", "health", "health_check"}:
            return super().handle_request(request)

        if action == "register_agent":
            return self._register_agent(request)

        if action == "get_agent_endpoint":
            return self._get_agent_endpoint(request)

        if action == "list_agents":
            return {
                "status": "success",
                "agents": self.backend.list_agents(),
            }

        return {"status": "error", "error": f"Unknown action: {action}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _register_agent(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an agent registration request."""
        registration_data = request.get("registration_data") or request

        try:
            # Accept either already-validated AgentRegistration or raw dict.
            registration = (
                registration_data
                if isinstance(registration_data, AgentRegistration)
                else AgentRegistration(**registration_data)
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Invalid registration attempt: %s", exc)
            return {"status": "error", "error": str(exc)}

        agent_data = {
            "host": registration.host,
            "port": registration.port,
            "health_check_port": registration.health_check_port,
            "agent_type": registration.agent_type,
            "capabilities": registration.capabilities,
            "metadata": registration.metadata,
            "last_registered": datetime.utcnow().isoformat(),
        }
        
        self.backend.set(registration.agent_id, agent_data)

        logger.info("Registered agent %s @ %s:%s", registration.agent_id, registration.host, registration.port)
        return {"status": "success"}

    def _get_agent_endpoint(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch the endpoint data for a given agent."""
        agent_name = request.get("agent_name")
        if not agent_name:
            return {"status": "error", "error": "Missing 'agent_name'"}

        agent_data = self.backend.get(agent_name)
        if not agent_data:
            return {"status": "error", "error": f"Agent {agent_name} not found"}

        data = agent_data.copy()
        data.update({"status": "success"})
        return data
        
    def cleanup(self) -> None:
        """Clean up resources before shutdown."""
        if hasattr(self, 'backend'):
            self.backend.close()
        super().cleanup()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Service Registry Agent")
    parser.add_argument("--backend", choices=["memory", "redis"], default=DEFAULT_BACKEND,
                       help="Storage backend (default: memory)")
    parser.add_argument("--redis-url", default=DEFAULT_REDIS_URL,
                       help="Redis connection URL if using redis backend")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                       help="ZMQ port for agent communication")
    parser.add_argument("--health-check-port", type=int, default=DEFAULT_HEALTH_PORT,
                       help="HTTP port for health checks")
    
    args = parser.parse_args()
    
    agent = ServiceRegistryAgent(
        backend=args.backend,
        redis_url=args.redis_url,
        port=args.port,
        health_check_port=args.health_check_port
    )
    
    try:
        agent.run()
    except KeyboardInterrupt:
        logger.info("ServiceRegistryAgent interrupted; shutting down")
        agent.cleanup()
