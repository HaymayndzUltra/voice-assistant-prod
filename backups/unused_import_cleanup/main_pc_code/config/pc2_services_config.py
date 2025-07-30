"""
from common.config_manager import get_service_ip, get_service_url, get_redis_url
PC2 Services Configuration Loader
--------------------------------
Utility module for loading PC2 services configuration
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from functools import lru_cache

# Standardized environment variables (Blueprint.md Step 4)
from common.utils.env_standardizer import get_mainpc_ip, get_pc2_ip, get_current_machine, get_env

logger = logging.getLogger("PC2Config")

@lru_cache(maxsize=1)
def load_pc2_services() -> Dict[str, Any]:
    """
    Load PC2 services configuration from YAML file
    
    Returns:
        Dictionary containing PC2 services configuration
    """
    try:
        # Try to load from pc2_services.yaml
        config_dir = Path(__file__).parent
        pc2_config_path = config_dir / "pc2_services.yaml"
        
        if pc2_config_path.exists():
            with open(pc2_config_path, 'r') as f:
                pc2_config = yaml.safe_load(f)
                logger.info(f"Loaded PC2 services from {pc2_config_path}")
                return pc2_config
        else:
            logger.warning(f"PC2 services configuration not found at {pc2_config_path}")
            # Return default configuration
            return {
                "enabled": False,
                "ip": get_pc2_ip(),
                "hostname": "PC2"
            }
    except Exception as e:
        logger.error(f"Error loading PC2 services configuration: {e}")
        return {"enabled": False}

@lru_cache(maxsize=32)
def get_service_connection(service_name: str) -> Optional[str]:
    """
    Get connection string for a PC2 service
    
    Args:
        service_name: Name of the service
        
    Returns:
        Connection string in format "tcp://IP:PORT" or None if service not found
    """
    try:
        pc2_config = load_pc2_services()
        
        if not pc2_config.get("enabled", False):
            logger.warning("PC2 services not enabled")
            return None
            
        if service_name not in pc2_config:
            logger.warning(f"Service {service_name} not found in PC2 configuration")
            return None
            
        service_config = pc2_config[service_name]
        if not isinstance(service_config, dict) or not service_config.get("enabled", False):
            logger.warning(f"Service {service_name} is disabled")
            return None
            
        pc2_ip = pc2_config.get("ip", get_pc2_ip())
        port = service_config.get("port")
        
        if not port:
            logger.warning(f"No port specified for service {service_name}")
            return None
            
        return f"tcp://{pc2_ip}:{port}"
    except Exception as e:
        logger.error(f"Error getting connection for service {service_name}: {e}")
        return None

def list_available_services() -> Dict[str, Dict[str, Any]]:
    """
    List all available PC2 services
    
    Returns:
        Dictionary of service names and their configurations
    """
    pc2_config = load_pc2_services()
    
    if not pc2_config.get("enabled", False):
        logger.warning("PC2 services not enabled")
        return {}
        
    services = {}
    
    for name, config in pc2_config.items():
        if isinstance(config, dict) and config.get("enabled", False):
            services[name] = config
            
    return services

def reload_configuration():
    """
    Force reload of configuration by clearing the cache
    """
    load_pc2_services.cache_clear()
    get_service_connection.cache_clear()
    logger.info("PC2 services configuration cache cleared")

# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    pc2_config = load_pc2_services()
    print(f"PC2 services enabled: {pc2_config.get('enabled', False)}")
    
    if pc2_config.get("enabled", False):
        print(f"PC2 IP: {pc2_config.get('ip')}")
        
        services = list_available_services()
        print(f"Available services: {len(services)}")
        
        for name, config in services.items():
            connection = get_service_connection(name)
            print(f"- {name}: {connection} ({config.get('description', 'No description')})") 