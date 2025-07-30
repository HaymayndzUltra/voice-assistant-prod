"""
Unified Configuration Manager
Phase 1 Week 2 Day 2 - Standardize configuration loading across all BaseAgent instances
"""

import os
import yaml
import json
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from functools import lru_cache
import threading

from common.utils.path_manager import PathManager


@dataclass
class ConfigSource:
    """Configuration source metadata"""
    path: str
    type: str  # 'yaml', 'json', 'env'
    priority: int  # Lower number = higher priority
    last_modified: float
    cache_ttl: int = 300  # 5 minutes default


class UnifiedConfigManager:
    """
    Unified configuration manager that standardizes config loading
    across MainPC (load_unified_config) and PC2 (Config().get_config()) patterns
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._config_cache = {}
        self._config_sources = []
        self._cache_lock = threading.RLock()
        
        # Initialize default configuration sources
        self._setup_default_sources()
    
    def _setup_default_sources(self):
        """Set up default configuration sources in priority order"""
        project_root = PathManager.get_project_root()
        
        # Priority order (lower number = higher priority)
        default_sources = [
            # Environment-specific configs (highest priority)
            ConfigSource(
                path=os.path.join(project_root, "config", "local.yaml"),
                type="yaml",
                priority=1,
                last_modified=0
            ),
            
            # MainPC startup config
            ConfigSource(
                path=os.path.join(project_root, "main_pc_code", "config", "startup_config.yaml"),
                type="yaml", 
                priority=2,
                last_modified=0
            ),
            
            # PC2 startup config
            ConfigSource(
                path=os.path.join(project_root, "pc2_code", "config", "startup_config.yaml"),
                type="yaml",
                priority=3,
                last_modified=0
            ),
            
            # Global system config
            ConfigSource(
                path=os.path.join(project_root, "config", "system_config.yaml"),
                type="yaml",
                priority=4,
                last_modified=0
            ),
            
            # Fallback JSON configs
            ConfigSource(
                path=os.path.join(project_root, "config", "default_config.json"),
                type="json",
                priority=5,
                last_modified=0
            )
        ]
        
        # Only add sources that exist
        for source in default_sources:
            if os.path.exists(source.path):
                source.last_modified = os.path.getmtime(source.path)
                self._config_sources.append(source)
    
    def _load_config_file(self, source: ConfigSource) -> Dict[str, Any]:
        """Load configuration from a single source"""
        try:
            with open(source.path, 'r', encoding='utf-8') as f:
                if source.type == 'yaml':
                    return yaml.safe_load(f) or {}
                elif source.type == 'json':
                    return json.load(f) or {}
                else:
                    return {}
        except Exception:
            # Silently ignore config file errors to maintain backward compatibility
            return {}
    
    def _merge_configs(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple configuration dictionaries with priority handling"""
        merged = {}
        
        # Process configs in reverse priority order (highest priority last)
        for config in sorted(configs, key=lambda x: x.get('_priority', 999)):
            config.pop('_priority', None)
            self._deep_merge(merged, config)
        
        return merged
    
    def _deep_merge(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Deep merge source into target dictionary"""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached config is still valid"""
        if cache_key not in self._config_cache:
            return False
        
        cache_entry = self._config_cache[cache_key]
        cache_time = cache_entry.get('_cache_time', 0)
        cache_ttl = cache_entry.get('_cache_ttl', 300)
        
        # Check TTL
        if time.time() - cache_time > cache_ttl:
            return False
        
        # Check file modifications
        for source in self._config_sources:
            if os.path.exists(source.path):
                current_mtime = os.path.getmtime(source.path)
                if current_mtime > source.last_modified:
                    return False
        
        return True
    
    @lru_cache(maxsize=128)
    def get_agent_config(self, agent_name: str, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get unified configuration for an agent
        
        Args:
            agent_name: Name of the agent requesting config
            config_path: Optional specific config file path
            
        Returns:
            Unified configuration dictionary
        """
        cache_key = f"{agent_name}:{config_path or 'default'}"
        
        with self._cache_lock:
            # Check cache validity
            if self._is_cache_valid(cache_key):
                return self._config_cache[cache_key].copy()
            
            # Load fresh config
            configs = []
            
            # Load from all sources
            for source in self._config_sources:
                config_data = self._load_config_file(source)
                if config_data:
                    config_data['_priority'] = source.priority
                    configs.append(config_data)
            
            # Load specific config file if provided
            if config_path and os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                            specific_config = yaml.safe_load(f) or {}
                        else:
                            specific_config = json.load(f) or {}
                    specific_config['_priority'] = 0  # Highest priority
                    configs.append(specific_config)
                except Exception:
                    pass
            
            # Merge all configs
            merged_config = self._merge_configs(configs)
            
            # Extract agent-specific config if available
            agent_config = merged_config.get('agents', {}).get(agent_name, {})
            
            # Merge agent-specific with global settings
            final_config = merged_config.copy()
            final_config.update(agent_config)
            
            # Add cache metadata
            final_config['_cache_time'] = time.time()
            final_config['_cache_ttl'] = 300
            final_config['_agent_name'] = agent_name
            
            # Cache the result
            self._config_cache[cache_key] = final_config.copy()
            
            return final_config
    
    def get_global_config(self) -> Dict[str, Any]:
        """Get global system configuration"""
        return self.get_agent_config('_global_')
    
    def clear_cache(self):
        """Clear configuration cache"""
        with self._cache_lock:
            self._config_cache.clear()
            self.get_agent_config.cache_clear()
    
    def reload_config(self):
        """Force reload of all configuration sources"""
        # Update file modification times
        for source in self._config_sources:
            if os.path.exists(source.path):
                source.last_modified = os.path.getmtime(source.path)
        
        # Clear cache to force reload
        self.clear_cache()


# Convenience functions for backward compatibility

def load_unified_config(config_path: Optional[str] = None, agent_name: str = "unknown") -> Dict[str, Any]:
    """
    MainPC-style configuration loading (backward compatible)
    
    Args:
        config_path: Optional path to specific config file
        agent_name: Name of the requesting agent
        
    Returns:
        Unified configuration dictionary
    """
    manager = UnifiedConfigManager()
    return manager.get_agent_config(agent_name, config_path)


class Config:
    """
    PC2-style configuration class (backward compatible)
    """
    
    def __init__(self):
        self._manager = UnifiedConfigManager()
    
    def get_config(self, agent_name: str = "unknown") -> Dict[str, Any]:
        """
        PC2-style configuration loading (backward compatible)
        
        Args:
            agent_name: Name of the requesting agent
            
        Returns:
            Unified configuration dictionary
        """
        return self._manager.get_agent_config(agent_name)


# Enhanced BaseAgent configuration integration

class BaseAgentConfigMixin:
    """
    Mixin to add unified configuration support to BaseAgent
    """
    
    def _load_unified_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration using unified configuration manager
        
        Args:
            config_path: Optional specific config file path
            
        Returns:
            Agent configuration dictionary
        """
        agent_name = getattr(self, 'name', self.__class__.__name__)
        manager = UnifiedConfigManager()
        
        config = manager.get_agent_config(agent_name, config_path)
        
        # Apply configuration defaults for BaseAgent
        config.setdefault('port', getattr(self, 'port', 5000))
        config.setdefault('health_check_port', getattr(self, 'health_check_port', config['port'] + 1))
        config.setdefault('zmq_request_timeout', 5000)
        config.setdefault('enable_metrics', True)
        config.setdefault('enable_health_check', True)
        
        return config
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a specific configuration value with fallback
        
        Args:
            key: Configuration key (supports dot notation like 'db.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        config = getattr(self, 'config', {})
        
        # Support dot notation for nested keys
        keys = key.split('.')
        value = config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def reload_config(self):
        """Reload agent configuration"""
        if hasattr(self, '_load_unified_config'):
            self.config = self._load_unified_config()
            
            # Update dynamic properties
            if 'port' in self.config:
                old_port = getattr(self, 'port', None)
                new_port = self.config['port']
                if old_port != new_port:
                    # Port change would require restart, log warning
                    import logging
                    logger = logging.getLogger(self.__class__.__name__)
                    logger.warning(f"Port change detected ({old_port} -> {new_port}), restart required")


# Global instance for easy access
_unified_config_manager = UnifiedConfigManager()

def get_unified_config_manager() -> UnifiedConfigManager:
    """Get the global unified configuration manager instance"""
    return _unified_config_manager 