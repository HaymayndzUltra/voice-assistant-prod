"""
Environment-Aware Configuration Manager
Builds on common/env_helpers.py to provide intelligent environment configuration
Handles development, production, testing, and container environments
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from common.env_helpers import get_env, get_int

class ConfigManager:
    """Intelligent configuration manager that adapts to environment"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._find_config_file()
        self.env_type = get_env('ENV_TYPE', 'development')
        self._config_cache = None
        
    def _find_config_file(self) -> str:
        """Find the environment configuration file"""
        possible_paths = [
            'config/environment.yaml',
            '../config/environment.yaml',
            '../../config/environment.yaml',
            os.path.join(os.path.dirname(__file__), '..', 'config', 'environment.yaml')
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
        # Create default if not found
        return 'config/environment.yaml'
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration for current environment"""
        if self._config_cache is not None:
            return self._config_cache
            
        try:
            with open(self.config_file, 'r') as f:
                all_configs = yaml.safe_load(f)
        except FileNotFoundError:
            # Return sensible defaults if config file missing
            all_configs = self._get_default_config()
        
        # Get config for current environment
        env_config = all_configs.get(self.env_type, all_configs.get('development', {}))
        
        # Process environment variable substitutions
        self._config_cache = self._process_env_vars(env_config)
        return self._config_cache
    
    def _process_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process ${VAR} substitutions using env_helpers"""
        processed = {}
        
        for key, value in config.items():
            if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                # Extract variable name and default
                var_spec = value[2:-1]  # Remove ${ and }
                if ':-' in var_spec:
                    var_name, default_val = var_spec.split(':-', 1)
                else:
                    var_name, default_val = var_spec, None
                
                # Use env_helpers to get value
                processed[key] = get_env(var_name, default_val)
            elif isinstance(value, dict):
                processed[key] = self._process_env_vars(value)
            else:
                processed[key] = value
                
        return processed
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Provide sensible defaults if config file is missing"""
        return {
            'development': {
                'mainpc_ip': '192.168.100.16',
                'pc2_ip': '192.168.100.17',
                'service_registry_host': '192.168.100.16',
                'redis_host': '192.168.100.16',
                'redis_port': 6379,
                'debug_mode': True,
                'log_level': 'DEBUG'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        config = self.load_config()
        return config.get(key, default)
    
    def get_ip(self, service: str) -> str:
        """Get IP address for a service"""
        config = self.load_config()
        
        ip_mappings = {
            'mainpc': config.get('mainpc_ip', '192.168.100.16'),
            'pc2': config.get('pc2_ip', '192.168.100.17'),
            'service_registry': config.get('service_registry_host', '192.168.100.16'),
            'redis': config.get('redis_host', '192.168.100.16')
        }
        
        return ip_mappings.get(service, config.get(f'{service}_ip', '127.0.0.1'))
    
    def get_port(self, service: str, default_port: int) -> int:
        """Get port for a service"""
        config = self.load_config()
        return config.get(f'{service}_port', default_port)
    
    def get_redis_url(self) -> str:
        """Get complete Redis URL"""
        config = self.load_config()
        host = config.get('redis_host', '192.168.100.16')
        port = config.get('redis_port', 6379)
        db = config.get('redis_db', 0)
        return f"redis://{host}:{port}/{db}"
    
    def get_zmq_url(self, service: str, port: int) -> str:
        """Get ZMQ URL for a service"""
        ip = self.get_ip(service)
        return f"tcp://{ip}:{port}"
    
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.env_type == 'development'
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.env_type == 'production'
    
    def is_container(self) -> bool:
        """Check if running in container environment"""
        return self.env_type == 'container' or get_env('DOCKER_ENV', 'false').lower() == 'true'


# Global instance for easy access
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_service_ip(service: str) -> str:
    """Convenience function to get service IP"""
    return get_config_manager().get_ip(service)

def get_service_url(service: str, port: int) -> str:
    """Convenience function to get service ZMQ URL"""
    return get_config_manager().get_zmq_url(service, port)

def get_redis_url() -> str:
    """Convenience function to get Redis URL"""
    return get_config_manager().get_redis_url() 