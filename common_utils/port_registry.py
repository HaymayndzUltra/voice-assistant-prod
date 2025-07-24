#!/usr/bin/env python3
"""port_registry.py

Centralized port registry that loads from config/ports.yaml and provides
get_port() function for agents to request their assigned ports.

Features:
- Loads port assignments from YAML configuration
- Runtime validation for duplicate agent name requests
- Fallback to environment variables
- Thread-safe operations
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Dict, Optional

try:
    import yaml
except ImportError:
    yaml = None

# Thread-safe singleton pattern
_port_registry: Optional[PortRegistry] = None
_registry_lock = threading.Lock()


class PortRegistryError(Exception):
    """Raised when port registry operations fail."""
    pass


class PortRegistry:
    """Central port registry for all agents and services."""
    
    def __init__(self, config_path: str = "config/ports.yaml"):
        self.config_path = Path(config_path)
        self._ports: Dict[str, int] = {}
        self._purpose_map: Dict[str, str] = {}
        self._owner_map: Dict[str, str] = {}
        self._agent_requests: Dict[str, int] = {}  # Track which agent requested which port
        self._lock = threading.Lock()
        self._load_config()
    
    def _load_config(self) -> None:
        """Load port configuration from YAML file."""
        if not self.config_path.exists():
            raise PortRegistryError(f"Port config file not found: {self.config_path}")
        
        if yaml is None:
            raise PortRegistryError("PyYAML not available; cannot load port config")
        
        try:
            with self.config_path.open('r') as f:
                entries = yaml.safe_load(f) or []
            
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                
                port = entry.get('port')
                purpose = entry.get('purpose', 'Unknown')
                owner = entry.get('owner', 'Unknown')
                
                if port is None:
                    continue
                
                # Use purpose as the key for get_port() lookups
                key = purpose.split(' / ')[0].strip()  # Take first part if multiple purposes
                self._ports[key] = port
                self._purpose_map[key] = purpose
                self._owner_map[key] = owner
                
        except Exception as e:
            raise PortRegistryError(f"Failed to load port config: {e}") from e
    
    def get_port(self, agent_name: str, fallback_env_var: Optional[str] = None) -> int:
        """
        Get port for an agent by name.
        
        Args:
            agent_name: Name of the agent/service (e.g., "MEMORY_AGENT", "Model Manager Suite")
            fallback_env_var: Optional environment variable to check if not found in config
            
        Returns:
            Port number
            
        Raises:
            PortRegistryError: If agent not found and no fallback available
        """
        with self._lock:
            # Try exact match first
            if agent_name in self._ports:
                port = self._ports[agent_name]
                self._check_duplicate_request(agent_name, port)
                return port
            
            # Try case-insensitive partial match
            agent_lower = agent_name.lower()
            for key, port in self._ports.items():
                if agent_lower in key.lower() or key.lower() in agent_lower:
                    self._check_duplicate_request(agent_name, port)
                    return port
            
            # Try environment variable fallback
            if fallback_env_var and fallback_env_var in os.environ:
                try:
                    port = int(os.environ[fallback_env_var])
                    self._check_duplicate_request(agent_name, port)
                    return port
                except ValueError:
                    pass
            
            raise PortRegistryError(
                f"Port not found for agent '{agent_name}'. "
                f"Available keys: {list(self._ports.keys())}"
            )
    
    def _check_duplicate_request(self, agent_name: str, port: int) -> None:
        """Check if two different agent names are requesting the same port."""
        if port in self._agent_requests.values():
            existing_agent = next(
                name for name, p in self._agent_requests.items() if p == port
            )
            if existing_agent != agent_name:
                raise PortRegistryError(
                    f"Port conflict: {agent_name} and {existing_agent} both requesting port {port}"
                )
        
        self._agent_requests[agent_name] = port
    
    def list_ports(self) -> Dict[str, Dict[str, any]]:
        """Return all registered ports with metadata."""
        with self._lock:
            return {
                key: {
                    'port': port,
                    'purpose': self._purpose_map.get(key, 'Unknown'),
                    'owner': self._owner_map.get(key, 'Unknown')
                }
                for key, port in self._ports.items()
            }
    
    def get_port_info(self, agent_name: str) -> Optional[Dict[str, any]]:
        """Get detailed port information for an agent."""
        with self._lock:
            if agent_name in self._ports:
                return {
                    'port': self._ports[agent_name],
                    'purpose': self._purpose_map.get(agent_name, 'Unknown'),
                    'owner': self._owner_map.get(agent_name, 'Unknown')
                }
            return None


def get_port_registry() -> PortRegistry:
    """Get singleton port registry instance."""
    global _port_registry
    if _port_registry is None:
        with _registry_lock:
            if _port_registry is None:
                _port_registry = PortRegistry()
    return _port_registry


def get_port(agent_name: str, fallback_env_var: Optional[str] = None) -> int:
    """
    Convenience function to get port for an agent.
    
    Usage:
        from common_utils.port_registry import get_port
        port = get_port("MEMORY_AGENT")
        port = get_port("Model Manager Suite")
    """
    return get_port_registry().get_port(agent_name, fallback_env_var)


def list_all_ports() -> Dict[str, Dict[str, any]]:
    """List all registered ports."""
    return get_port_registry().list_ports()


if __name__ == "__main__":
    # Simple CLI for testing
    import sys
    
    if len(sys.argv) > 1:
        try:
            port = get_port(sys.argv[1])
            print(f"{sys.argv[1]}: {port}")
        except PortRegistryError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("All registered ports:")
        for name, info in list_all_ports().items():
            print(f"  {name}: {info['port']} ({info['purpose']})") 