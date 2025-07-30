#!/usr/bin/env python3
"""
Unified Configuration Manager
Centralizes all configuration loading patterns across the AI System Monorepo.

This module replaces the 6 different configuration patterns identified in the codebase
with a single, consistent, cached, and validated configuration system.

Usage:
    from common.config.unified_config_manager import Config
    
    # Get configuration for current agent
    cfg = Config.for_agent(__file__)
    
    # Access configuration values with defaults
    port = cfg.int("ports.push", default=7102)
    redis_url = cfg.str("redis.url", default="redis://localhost:6379/0")
    timeout = cfg.float("network.timeout.request", default=30.0)
    debug = cfg.bool("system.debug_mode", default=False)
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from functools import lru_cache
from threading import Lock


class ConfigError(Exception):
    """Configuration-related errors."""
    pass


class ConfigValue:
    """Wrapper for configuration values with type conversion and validation."""
    
    def __init__(self, value: Any, path: str):
        self._value = value
        self._path = path
    
    def get(self, default: Any = None) -> Any:
        """Get the raw value with optional default."""
        return self._value if self._value is not None else default
    
    def str(self, default: str = "") -> str:
        """Get value as string."""
        if self._value is None:
            return default
        return str(self._value)
    
    def int(self, default: int = 0) -> int:
        """Get value as integer."""
        if self._value is None:
            return default
        try:
            return int(self._value)
        except (ValueError, TypeError) as e:
            raise ConfigError(f"Cannot convert '{self._value}' to int at path '{self._path}'") from e
    
    def float(self, default: float = 0.0) -> float:
        """Get value as float."""
        if self._value is None:
            return default
        try:
            return float(self._value)
        except (ValueError, TypeError) as e:
            raise ConfigError(f"Cannot convert '{self._value}' to float at path '{self._path}'") from e
    
    def bool(self, default: bool = False) -> bool:
        """Get value as boolean."""
        if self._value is None:
            return default
        if isinstance(self._value, bool):
            return self._value
        if isinstance(self._value, str):
            return self._value.lower() in ("true", "yes", "1", "on", "enabled")
        return bool(self._value)
    
    def list(self, default: List[Any] = None) -> List[Any]:
        """Get value as list."""
        if self._value is None:
            return default or []
        if isinstance(self._value, list):
            return self._value
        return [self._value]  # Single value wrapped in list
    
    def dict(self, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get value as dictionary."""
        if self._value is None:
            return default or {}
        if isinstance(self._value, dict):
            return self._value
        raise ConfigError(f"Cannot convert '{self._value}' to dict at path '{self._path}'")


class Config:
    """
    Unified Configuration Manager
    
    Provides centralized, cached, and validated configuration access
    with environment-specific overrides and fallback support.
    """
    
    _instances: Dict[str, 'Config'] = {}
    _cache_lock = Lock()
    _logger = logging.getLogger("ConfigManager")
    
    def __init__(self, agent_name: str, config_data: Dict[str, Any]):
        self.agent_name = agent_name
        self._config = config_data
        self._flat_config = self._flatten_dict(config_data)
    
    @classmethod
    def for_agent(cls, agent_file: str, environment: Optional[str] = None) -> 'Config':
        """
        Get configuration instance for an agent.
        
        Args:
            agent_file: Usually __file__ from the calling agent
            environment: Override environment (dev, prod, etc.)
        
        Returns:
            Config instance for the agent
        """
        agent_name = cls._extract_agent_name(agent_file)
        cache_key = f"{agent_name}_{environment or cls._get_environment()}"
        
        with cls._cache_lock:
            if cache_key not in cls._instances:
                config_data = cls._load_config(agent_name, environment)
                cls._instances[cache_key] = cls(agent_name, config_data)
                cls._logger.debug(f"Created config instance for {agent_name}")
            
            return cls._instances[cache_key]
    
    @classmethod
    def _extract_agent_name(cls, agent_file: str) -> str:
        """Extract agent name from file path."""
        path = Path(agent_file)
        agent_name = path.stem
        
        # Remove common suffixes
        for suffix in ["_agent", "_service", "_client"]:
            if agent_name.endswith(suffix):
                agent_name = agent_name[:-len(suffix)]
                break
        
        # Convert to PascalCase for consistency
        return ''.join(word.capitalize() for word in agent_name.split('_'))
    
    @classmethod
    def _get_environment(cls) -> str:
        """Get current environment from environment variables."""
        env = os.getenv("AI_SYSTEM_ENV", os.getenv("ENVIRONMENT", "development"))
        return env.lower()
    
    @classmethod
    def _get_config_root(cls) -> Path:
        """Get the configuration root directory."""
        # Find project root by looking for common files
        current_path = Path(__file__).parent
        for _ in range(10):  # Limit search depth
            if any((current_path / marker).exists() for marker in [
                "main_pc_code", "pc2_code", ".git", "setup.py", "pyproject.toml"
            ]):
                return current_path / "common" / "config"
            current_path = current_path.parent
        
        # Fallback to relative path
        return Path(__file__).parent
    
    @classmethod
    @lru_cache(maxsize=32)
    def _load_config(cls, agent_name: str, environment: Optional[str] = None) -> Dict[str, Any]:
        """Load and merge configuration files."""
        config_root = cls._get_config_root()
        environment = environment or cls._get_environment()
        
        # Load base configuration
        config = cls._load_yaml_file(config_root / "defaults" / "base.yaml")
        
        # Merge environment-specific configuration
        env_config_path = config_root / "defaults" / f"{environment}.yaml"
        if env_config_path.exists():
            env_config = cls._load_yaml_file(env_config_path)
            config = cls._merge_configs(config, env_config)
        
        # Load agent-specific configuration if it exists
        agent_config_path = config_root / "agents" / f"{agent_name.lower()}.yaml"
        if agent_config_path.exists():
            agent_config = cls._load_yaml_file(agent_config_path)
            config = cls._merge_configs(config, agent_config)
        
        # Apply environment variable overrides
        config = cls._apply_env_overrides(config)
        
        cls._logger.debug(f"Loaded config for {agent_name} in {environment} environment")
        return config
    
    @classmethod
    def _load_yaml_file(cls, file_path: Path) -> Dict[str, Any]:
        """Load YAML file with error handling."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            cls._logger.warning(f"Config file not found: {file_path}")
            return {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Error parsing YAML file {file_path}: {e}") from e
        except Exception as e:
            raise ConfigError(f"Error loading config file {file_path}: {e}") from e
    
    @classmethod
    def _merge_configs(cls, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two configuration dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._merge_configs(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @classmethod
    def _apply_env_overrides(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides using AI_SYSTEM_ prefix."""
        for env_var, env_value in os.environ.items():
            if env_var.startswith("AI_SYSTEM_"):
                # Convert AI_SYSTEM_REDIS_HOST to redis.host
                config_path = env_var[10:].lower().replace("_", ".")
                cls._set_nested_value(config, config_path, env_value)
        
        return config
    
    @classmethod
    def _set_nested_value(cls, config: Dict[str, Any], path: str, value: str):
        """Set a nested configuration value using dot notation."""
        keys = path.split('.')
        current = config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    @classmethod
    def _flatten_dict(cls, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten nested dictionary for easy access."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(cls._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    def get(self, path: str, default: Any = None) -> ConfigValue:
        """
        Get configuration value by dot-separated path.
        
        Args:
            path: Dot-separated path (e.g., "redis.host", "ports.push")
            default: Default value if path not found
        
        Returns:
            ConfigValue wrapper with type conversion methods
        """
        value = self._flat_config.get(path, default)
        return ConfigValue(value, path)
    
    # Convenience methods for common types
    def str(self, path: str, default: str = "") -> str:
        """Get string value."""
        return self.get(path, default).str(default)
    
    def int(self, path: str, default: int = 0) -> int:
        """Get integer value."""
        return self.get(path, default).int(default)
    
    def float(self, path: str, default: float = 0.0) -> float:
        """Get float value."""
        return self.get(path, default).float(default)
    
    def bool(self, path: str, default: bool = False) -> bool:
        """Get boolean value."""
        return self.get(path, default).bool(default)
    
    def list(self, path: str, default: List[Any] = None) -> List[Any]:
        """Get list value."""
        return self.get(path, default or []).list(default or [])
    
    def dict(self, path: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get dictionary value."""
        return self.get(path, default or {}).dict(default or {})
    
    def has(self, path: str) -> bool:
        """Check if configuration path exists."""
        return path in self._flat_config
    
    def all_keys(self) -> List[str]:
        """Get all available configuration keys."""
        return list(self._flat_config.keys())
    
    def dump(self) -> Dict[str, Any]:
        """Get complete configuration as dictionary."""
        return self._config.copy()
    
    def reload(self):
        """Reload configuration from files."""
        cache_key = f"{self.agent_name}_{self._get_environment()}"
        with self._cache_lock:
            if cache_key in self._instances:
                del self._instances[cache_key]
        
        # Clear LRU cache
        self._load_config.cache_clear()
        
        # Reload
        new_config = Config.for_agent(f"{self.agent_name}.py")
        self._config = new_config._config
        self._flat_config = new_config._flat_config


# Legacy compatibility functions
def load_unified_config(config_path: str) -> Dict[str, Any]:
    """Legacy compatibility function for old config loading patterns."""
    agent_name = Path(config_path).parent.parent.name
    config = Config.for_agent(f"{agent_name}.py")
    return config.dump()


def get_service_ip(service_name: str) -> str:
    """Legacy compatibility function."""
    config = Config.for_agent("system.py")
    return config.str(f"services.{service_name}.host", default="localhost")


def get_service_url(service_name: str) -> str:
    """Legacy compatibility function."""
    config = Config.for_agent("system.py")
    host = config.str(f"services.{service_name}.host", default="localhost")
    port = config.int(f"services.{service_name}.port", default=8000)
    return f"http://{host}:{port}"


def get_redis_url() -> str:
    """Legacy compatibility function."""
    config = Config.for_agent("system.py")
    host = config.str("redis.host", default="localhost")
    port = config.int("redis.port", default=6379)
    db = config.int("redis.db", default=0)
    return f"redis://{host}:{port}/{db}"


if __name__ == "__main__":
    # Test the configuration manager
    print("Configuration Manager Test:")
    
    # Test basic configuration loading
    config = Config.for_agent("test_agent.py")
    
    print(f"System name: {config.str('system.name')}")
    print(f"Debug mode: {config.bool('system.debug_mode')}")
    print(f"Log level: {config.str('logging.level')}")
    print(f"Redis host: {config.str('redis.host')}")
    print(f"Health interval: {config.int('health.interval_seconds')}")
    
    print(f"Available keys: {len(config.all_keys())}")
    print("Configuration loaded successfully!")
