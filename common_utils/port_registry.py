"""
Port Registry Module

Provides port allocation for agents. This is a minimal implementation for Docker containerization.
"""

import os
from typing import Dict, Optional

# Default port mappings for core agents
DEFAULT_PORTS: Dict[str, int] = {
    "ServiceRegistry": 7200,
    "SystemDigitalTwin": 7220,
    "RequestCoordinator": 26002,
    "ObservabilityHub": 9000,
    "UnifiedSystemAgent": 7225,
    "ModelManagerSuite": 7211,
}

def get_port(agent_name: str, offset: int = 0) -> int:
    """Get the port number for a given agent.
    
    Args:
        agent_name: Name of the agent
        offset: Port offset (from environment variables)
        
    Returns:
        Port number for the agent
        
    Raises:
        ValueError: If agent name is not found
    """
    # Try to get port from environment first
    env_var = f"{agent_name.upper()}_PORT"
    env_port = os.getenv(env_var)
    if env_port:
        return int(env_port) + offset
    
    # Fall back to default port mapping
    if agent_name in DEFAULT_PORTS:
        return DEFAULT_PORTS[agent_name] + offset
    
    # If not found, raise an error
    raise ValueError(f"No port configured for agent: {agent_name}")

def get_health_port(agent_name: str, offset: int = 0) -> int:
    """Get the health check port for a given agent.
    
    Args:
        agent_name: Name of the agent
        offset: Port offset
        
    Returns:
        Health check port number (main port + 1000)
    """
    main_port = get_port(agent_name, offset)
    return main_port + 1000

def list_agent_ports() -> Dict[str, int]:
    """List all configured agent ports.
    
    Returns:
        Dictionary mapping agent names to ports
    """
    return DEFAULT_PORTS.copy() 