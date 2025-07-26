#!/usr/bin/env python3
"""
Unified Configuration Loader v3

Supports the new v3 configuration format with machine-specific overrides.
This replaces the multiple scattered config loaders with a single, unified system.

Features:
- Single source of truth configuration (startup_config.v3.yaml)
- Machine-specific overrides (config/overrides/{machine}.yaml)
- Environment variable substitution
- Configuration validation and caching
- Backward compatibility with legacy config formats
"""

import os
import sys
import yaml
import logging
import threading
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
import copy

# Import PathManager for consistent path resolution
from .path_manager import PathManager

logger = logging.getLogger(__name__)

@dataclass
class ConfigMetadata:
    """Metadata about loaded configuration"""
    version: str = "3.0"
    machine: Optional[str] = None
    loaded_at: datetime = field(default_factory=datetime.now)
    config_files: List[str] = field(default_factory=list)
    overrides_applied: List[str] = field(default_factory=list)

class UnifiedConfigLoader:
    """
    Unified configuration loader for v3 format with machine overrides.
    
    Loading order:
    1. Load base startup_config.v3.yaml
    2. Apply machine-specific overrides from config/overrides/{machine}.yaml
    3. Apply environment variable overrides
    4. Validate and cache the final configuration
    """
    
    # Singleton instance
    _instance: Optional['UnifiedConfigLoader'] = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """Ensure singleton pattern."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(UnifiedConfigLoader, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the unified config loader."""
        with self._lock:
            if self._initialized:
                return
                
            # Configuration cache
            self._config_cache: Dict[str, Any] = {}
            self._metadata: Optional[ConfigMetadata] = None
            
            # Auto-detect machine type
            self._machine = self._detect_machine()
            
            # Configuration file paths
            self._base_config_path = PathManager.get_project_root() / "config" / "startup_config.v3.yaml"
            self._overrides_dir = PathManager.get_project_root() / "config" / "overrides"
            
            # Load configuration
            self._load_configuration()
            
            self._initialized = True
            logger.info(f"Unified config loader initialized for machine: {self._machine}")
    
    def _detect_machine(self) -> str:
        """Auto-detect machine type from environment or fallback logic."""
        # Check environment variable first
        machine = os.environ.get("MACHINE_TYPE") or os.environ.get("MACHINE_ROLE", "").lower()
        
        if machine in ["mainpc", "main_pc"]:
            return "mainpc"
        elif machine in ["pc2"]:
            return "pc2"
        
        # Additional checks: GPU detection or system info
        try:
            import subprocess
            gpu_info = subprocess.check_output(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]).decode().strip()
            if "RTX 4090" in gpu_info:
                return "mainpc"
            elif "RTX 3060" in gpu_info:
                return "pc2"
        except:
            pass
        
        # Fallback detection based on hostname or other indicators
        hostname = os.environ.get("HOSTNAME", "").lower()
        if "mainpc" in hostname or "main" in hostname:
            return "mainpc"
        elif "pc2" in hostname:
            return "pc2"
        
        # Default fallback with guidance
        logger.warning("Could not auto-detect machine type. Please set MACHINE_TYPE environment variable to 'mainpc' or 'pc2'. Defaulting to 'mainpc'")
        return "mainpc"
    
    def _load_configuration(self):
        """Load and merge configuration from base and override files."""
        config_files = []
        overrides_applied = []
        
        # 1. Load base configuration
        if not self._base_config_path.exists():
            logger.warning(f"Base config file not found: {self._base_config_path}")
            # Try fallback to legacy config
            return self._load_legacy_fallback()
        
        try:
            with open(self._base_config_path, 'r') as f:
                base_config = yaml.safe_load(f)
            config_files.append(str(self._base_config_path))
            logger.debug(f"Loaded base config: {self._base_config_path}")
        except Exception as e:
            logger.error(f"Error loading base config: {e}")
            return self._load_legacy_fallback()
        
        # 2. Process includes if present
        if "include" in base_config:
            included_configs = self._process_includes(base_config["include"])
            for included_config in included_configs:
                base_config = self._deep_merge(base_config, included_config)
            overrides_applied.append("includes")
            logger.debug(f"Processed {len(base_config['include'])} included configs")
        
        # 3. Apply machine-specific overrides
        machine_override_path = self._overrides_dir / f"{self._machine}.yaml"
        if machine_override_path.exists():
            try:
                with open(machine_override_path, 'r') as f:
                    machine_overrides = yaml.safe_load(f)
                
                base_config = self._deep_merge(base_config, machine_overrides)
                config_files.append(str(machine_override_path))
                overrides_applied.append(f"machine:{self._machine}")
                logger.debug(f"Applied machine overrides: {machine_override_path}")
            except Exception as e:
                logger.warning(f"Error loading machine overrides: {e}")
        
        # 4. Apply environment-specific overrides (docker, production, etc.)
        env_override = os.environ.get("CONFIG_OVERRIDE", "").lower()
        if env_override:
            env_override_path = self._overrides_dir / f"{env_override}.yaml"
            if env_override_path.exists():
                try:
                    with open(env_override_path, 'r') as f:
                        env_overrides = yaml.safe_load(f)
                    
                    base_config = self._deep_merge(base_config, env_overrides)
                    config_files.append(str(env_override_path))
                    overrides_applied.append(f"env:{env_override}")
                    logger.debug(f"Applied environment overrides: {env_override_path}")
                except Exception as e:
                    logger.warning(f"Error loading environment overrides: {e}")
        
        # 5. Apply environment variable substitutions
        base_config = self._substitute_environment_variables(base_config)
        if any("${" in str(v) for v in self._flatten_dict(base_config).values()):
            overrides_applied.append("env_vars")
        
        # 6. Filter agents based on machine profile
        base_config = self._filter_agents_for_machine(base_config)
        
        # Cache the final configuration
        self._config_cache = base_config
        self._metadata = ConfigMetadata(
            version=base_config.get("version", "3.0"),
            machine=self._machine,
            config_files=config_files,
            overrides_applied=overrides_applied
        )
        
        logger.info(f"Configuration loaded successfully: {len(config_files)} files, "
                   f"{len(overrides_applied)} overrides applied")
    
    def _load_legacy_fallback(self):
        """Fallback to legacy configuration loading."""
        logger.warning("Loading legacy configuration as fallback")
        
        # Try to load legacy startup_config.yaml
        legacy_paths = [
            PathManager.get_project_root() / "main_pc_code" / "config" / "startup_config.yaml",
            PathManager.get_project_root() / "pc2_code" / "config" / "startup_config.yaml",
            PathManager.get_project_root() / "config" / "startup_config.yaml"
        ]
        
        import warnings
        for path in legacy_paths:
            if path.exists():
                warnings.warn(
                    f"[DEPRECATION] Loading legacy config {path.name}; please migrate to startup_config.v3.yaml. This fallback will be removed in a future release.",
                    DeprecationWarning,
                )
                try:
                    with open(path, 'r') as f:
                        config = yaml.safe_load(f)
                    
                    # Convert to v3 format structure
                    self._config_cache = self._convert_legacy_to_v3(config)
                    self._metadata = ConfigMetadata(
                        version="2.0-legacy",
                        machine=self._machine,
                        config_files=[str(path)],
                        overrides_applied=["legacy_conversion"]
                    )
                    
                    logger.info(f"Loaded legacy config from: {path}")
                    return
                except Exception as e:
                    logger.warning(f"Error loading legacy config {path}: {e}")
        
        # Last resort: create minimal config
        self._config_cache = self._create_minimal_config()
        self._metadata = ConfigMetadata(
            version="3.0-minimal",
            machine=self._machine,
            config_files=[],
            overrides_applied=["minimal_fallback"]
        )
        logger.warning("Created minimal fallback configuration")
    
    def _process_includes(self, include_paths: List[str]) -> List[Dict[str, Any]]:
        """Process include directives and load the referenced configuration files."""
        included_configs = []
        project_root = PathManager.get_project_root()
        
        for include_path in include_paths:
            # Resolve relative paths from project root
            if not include_path.startswith('/'):
                full_path = project_root / include_path
            else:
                full_path = Path(include_path)
            
            if not full_path.exists():
                logger.warning(f"Included config file not found: {full_path}")
                continue
            
            try:
                with open(full_path, 'r') as f:
                    included_config = yaml.safe_load(f)
                included_configs.append(included_config)
                logger.debug(f"Loaded included config: {full_path}")
            except Exception as e:
                logger.error(f"Error loading included config {full_path}: {e}")
        
        return included_configs
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries, with override taking precedence."""
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    def _substitute_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute environment variables in configuration values."""
        def substitute_value(value):
            if isinstance(value, str):
                # Handle ${VAR} and ${VAR}+offset syntax
                import re
                def replace_env_var(match):
                    var_expr = match.group(1)
                    if '+' in var_expr:
                        var_name, offset = var_expr.split('+', 1)
                        base_value = int(os.environ.get(var_name.strip(), '0'))
                        return str(base_value + int(offset.strip()))
                    else:
                        return os.environ.get(var_expr.strip(), match.group(0))
                
                return re.sub(r'\$\{([^}]+)\}', replace_env_var, value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        return substitute_value(config)
    
    def _filter_agents_for_machine(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Filter agent groups and agents based on machine profile."""
        machine_profile = config.get("machine_profiles", {}).get(self._machine, {})
        enabled_groups = machine_profile.get("enabled_groups", [])
        
        if not enabled_groups:
            logger.warning(f"No enabled groups found for machine {self._machine}")
            return config
        
        # Filter agent_groups to only include enabled groups
        filtered_groups = {}
        for group_name, agents in config.get("agent_groups", {}).items():
            if group_name in enabled_groups:
                filtered_groups[group_name] = agents
        
        config["agent_groups"] = filtered_groups
        
        # Apply machine-specific disabled agents
        override_path = self._overrides_dir / f"{self._machine}.yaml"
        if override_path.exists():
            try:
                with open(override_path, 'r') as f:
                    machine_config = yaml.safe_load(f)
                
                disabled_agents = machine_config.get("disabled_agents", [])
                for group_name, agents in config["agent_groups"].items():
                    config["agent_groups"][group_name] = {
                        name: agent for name, agent in agents.items() 
                        if name not in disabled_agents
                    }
            except Exception as e:
                logger.warning(f"Error applying agent filters: {e}")
        
        logger.debug(f"Filtered to {len(enabled_groups)} agent groups for machine {self._machine}")
        return config
    
    def _convert_legacy_to_v3(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy configuration format to v3 structure."""
        # Basic conversion - this would need to be expanded based on legacy formats
        v3_config = {
            "version": "2.0-legacy",
            "global_settings": legacy_config.get("global_settings", {}),
            "agent_groups": legacy_config.get("agent_groups", legacy_config.get("agents", {})),
            "machine_profiles": {
                self._machine: {
                    "enabled_groups": list(legacy_config.get("agent_groups", {}).keys())
                }
            }
        }
        return v3_config
    
    def _create_minimal_config(self) -> Dict[str, Any]:
        """Create a minimal working configuration."""
        return {
            "version": "3.0-minimal",
            "global_settings": {
                "environment": {
                    "LOG_LEVEL": "INFO",
                    "DEBUG_MODE": "false"
                },
                "resource_limits": {
                    "cpu_percent": 80,
                    "memory_mb": 2048,
                    "max_threads": 4
                }
            },
            "agent_groups": {
                "core_services": {
                    "ServiceRegistry": {
                        "script_path": "main_pc_code/agents/service_registry_agent.py",
                        "port": 7100,
                        "health_check_port": 8100,
                        "required": True,
                        "dependencies": []
                    }
                }
            },
            "machine_profiles": {
                self._machine: {
                    "enabled_groups": ["core_services"]
                }
            }
        }
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """Flatten a nested dictionary for easier processing."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)
    
    # Public API methods
    
    def get_config(self) -> Dict[str, Any]:
        """Get the complete loaded configuration."""
        return copy.deepcopy(self._config_cache)
    
    def get_global_settings(self) -> Dict[str, Any]:
        """Get global settings section."""
        return self._config_cache.get("global_settings", {})
    
    def get_agent_groups(self) -> Dict[str, Any]:
        """Get agent groups configuration."""
        return self._config_cache.get("agent_groups", {})
    
    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific agent."""
        for group_name, agents in self.get_agent_groups().items():
            if agent_name in agents:
                return agents[agent_name]
        return None
    
    def get_machine_profile(self) -> Dict[str, Any]:
        """Get the current machine's profile."""
        return self._config_cache.get("machine_profiles", {}).get(self._machine, {})
    
    def get_metadata(self) -> ConfigMetadata:
        """Get configuration metadata."""
        return self._metadata
    
    def reload(self):
        """Reload configuration from files."""
        logger.info("Reloading configuration...")
        self._load_configuration()
    
    def get_machine_type(self) -> str:
        """Get the detected machine type."""
        return self._machine

# Global singleton instance
_unified_loader: Optional[UnifiedConfigLoader] = None

def get_unified_config() -> UnifiedConfigLoader:
    """Get the global unified configuration loader instance."""
    global _unified_loader
    if _unified_loader is None:
        _unified_loader = UnifiedConfigLoader()
    return _unified_loader

# Convenience functions for common operations
def get_config() -> Dict[str, Any]:
    """Get the complete configuration."""
    return get_unified_config().get_config()

def get_global_settings() -> Dict[str, Any]:
    """Get global settings."""
    return get_unified_config().get_global_settings()

def get_agent_config(agent_name: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a specific agent."""
    return get_unified_config().get_agent_config(agent_name)

def get_machine_type() -> str:
    """Get the detected machine type."""
    return get_unified_config().get_machine_type()

def reload_config():
    """Reload configuration from files."""
    get_unified_config().reload() 