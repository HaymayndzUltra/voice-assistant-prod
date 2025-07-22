"""
Universal Configuration Manager
Handles both MainPC (agent_groups) and PC2 (pc2_services) formats
"""
import yaml
import os
from pathlib import Path
from typing import Dict, List, Any, Union

def load_unified_config(config_path: str = None) -> Dict[str, Any]:
    """
    Load config and normalize to standard format regardless of source
    Returns: Unified agent list with standard fields
    """
    if config_path is None:
        # Default to MainPC config
        config_path = "main_pc_code/config/startup_config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    if 'agent_groups' in config:
        return normalize_mainpc_config(config)
    elif 'pc2_services' in config:
        return normalize_pc2_config(config)
    else:
        raise ValueError(f"Unknown config format in {config_path}")

def normalize_mainpc_config(config: Dict) -> Dict[str, Any]:
    """Convert MainPC agent_groups to unified format"""
    unified_agents = []
    
    for group_name, agents in config['agent_groups'].items():
        for agent_name, agent_data in agents.items():
            unified_agent = {
                'name': agent_name,
                'group': group_name,
                'script_path': agent_data.get('script_path'),
                'port': agent_data.get('port'),
                'health_check_port': agent_data.get('health_check_port'),
                'required': agent_data.get('required', False),
                'dependencies': agent_data.get('dependencies', []),
                'config': agent_data.get('config', {}),
                'machine': 'mainpc'
            }
            unified_agents.append(unified_agent)
    
    return {
        'unified_agents': unified_agents,
        'global_settings': config.get('global_settings', {}),
        'source_format': 'agent_groups'
    }

def normalize_pc2_config(config: Dict) -> Dict[str, Any]:
    """Convert PC2 pc2_services to unified format"""
    unified_agents = []
    
    for agent_data in config['pc2_services']:
        unified_agent = {
            'name': agent_data.get('name'),
            'group': 'pc2_services',  # Default group for PC2
            'script_path': agent_data.get('script_path'),
            'port': agent_data.get('port'),
            'health_check_port': agent_data.get('health_check_port'),
            'required': agent_data.get('required', False),
            'dependencies': agent_data.get('dependencies', []),
            'config': agent_data.get('config', {}),
            'machine': 'pc2'
        }
        unified_agents.append(unified_agent)
    
    return {
        'unified_agents': unified_agents,
        'global_settings': {
            'environment': config.get('environment', {}),
            'resource_limits': config.get('resource_limits', {}),
            'health_checks': config.get('health_checks', {})
        },
        'source_format': 'pc2_services'
    }

def get_agents_by_machine(unified_config: Dict, machine: str) -> List[Dict]:
    """Filter agents by machine type"""
    return [agent for agent in unified_config['unified_agents'] 
            if agent['machine'] == machine]

def validate_config_consistency(unified_config: Dict) -> List[str]:
    """Validate configuration for common issues"""
    issues = []
    ports_used = set()
    
    for agent in unified_config['unified_agents']:
        # Check port conflicts
        port = agent.get('port')
        health_port = agent.get('health_check_port')
        
        if port in ports_used:
            issues.append(f"Port conflict: {port} used by multiple agents")
        if health_port in ports_used:
            issues.append(f"Health port conflict: {health_port} used by multiple agents")
        
        if port:
            ports_used.add(port)
        if health_port:
            ports_used.add(health_port)
        
        # Check script path exists
        script_path = agent.get('script_path')
        if script_path and not os.path.exists(script_path):
            issues.append(f"Script not found: {script_path} for agent {agent['name']}")
    
    return issues

# =====================================================================
#                    LEGACY COMPATIBILITY FUNCTIONS
# =====================================================================
# These functions maintain compatibility with existing agent code

def get_service_ip(service_name: str) -> str:
    """
    Get IP address for a service - maintains compatibility with existing code
    
    Args:
        service_name: Service identifier (mainpc, pc2, redis, nats, etc.)
    
    Returns:
        IP address for the service
    """
    # Default IP mappings for common services
    service_ips = {
        "mainpc": os.environ.get("MAIN_PC_IP", "192.168.100.16"),
        "pc2": os.environ.get("PC2_IP", "192.168.100.17"),
        "redis": os.environ.get("REDIS_HOST", "192.168.100.16"),
        "nats": os.environ.get("NATS_HOST", "192.168.100.16"),
        "service_registry": os.environ.get("SERVICE_REGISTRY_HOST", "192.168.100.16"),
        "localhost": "127.0.0.1",
        "docker": "host.docker.internal",
    }
    
    # Check if running in Docker container
    if os.path.exists("/.dockerenv"):
        # In Docker, use service names instead of IPs
        docker_services = {
            "mainpc": "mainpc",
            "pc2": "pc2", 
            "redis": "redis",
            "nats": "nats",
            "service_registry": "service_registry"
        }
        return docker_services.get(service_name, service_name)
    
    return service_ips.get(service_name, service_name)

def get_service_url(service_name: str, port: int = None, protocol: str = "http") -> str:
    """
    Get full URL for a service
    
    Args:
        service_name: Service identifier
        port: Port number (optional)
        protocol: Protocol (http, https, tcp, etc.)
    
    Returns:
        Full service URL
    """
    ip = get_service_ip(service_name)
    
    if port:
        return f"{protocol}://{ip}:{port}"
    else:
        # Default ports for common services
        default_ports = {
            "redis": 6379,
            "nats": 4222,
            "service_registry": 7001,
        }
        default_port = default_ports.get(service_name, 80)
        return f"{protocol}://{ip}:{default_port}"

def get_redis_url(database: int = 0) -> str:
    """
    Get Redis connection URL
    
    Args:
        database: Redis database number
    
    Returns:
        Redis URL
    """
    redis_host = get_service_ip("redis")
    redis_port = os.environ.get("REDIS_PORT", "6379")
    return f"redis://{redis_host}:{redis_port}/{database}"