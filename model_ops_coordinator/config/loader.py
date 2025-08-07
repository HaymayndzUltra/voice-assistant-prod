"""Unified configuration loader for ModelOps Coordinator."""

import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
import re
from dataclasses import dataclass

from ..core.schemas import Config
from ..core.errors import ConfigurationError


@dataclass
class ConfigSource:
    """Configuration source metadata."""
    path: str
    type: str  # 'yaml', 'env', 'default'
    priority: int  # Lower numbers = higher priority
    loaded: bool = False
    data: Optional[Dict[str, Any]] = None


class UnifiedConfigLoader:
    """
    Unified configuration loader supporting YAML files and environment variables.
    
    Loads configuration from multiple sources with priority-based merging:
    1. Environment variables (highest priority)
    2. Local config files (medium priority)
    3. Default config (lowest priority)
    
    Supports environment variable interpolation in YAML files using ${VAR:default} syntax.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.sources: List[ConfigSource] = []
        self.loaded_config: Optional[Dict[str, Any]] = None
        
        # Environment variable prefix for ModelOps
        self.env_prefix = "MOC_"
        
        # Default configuration search order
        self.config_files = [
            "default.yaml",
            "local.yaml",
            "production.yaml",
            "development.yaml"
        ]
    
    def load_config(self, config_file: Optional[str] = None) -> Config:
        """
        Load and merge configuration from all sources.
        
        Args:
            config_file: Optional specific config file to load
            
        Returns:
            Validated Config object
        """
        # Reset state
        self.sources.clear()
        self.loaded_config = None
        
        # Determine config files to load
        if config_file:
            config_files = [config_file]
        else:
            config_files = self._discover_config_files()
        
        # Load YAML configurations
        for file_path in config_files:
            self._load_yaml_source(file_path)
        
        # Load environment variables
        self._load_environment_source()
        
        # Merge all sources
        merged_config = self._merge_sources()
        
        # Perform environment variable substitution
        resolved_config = self._resolve_environment_variables(merged_config)
        
        # Validate and create Config object
        try:
            config = Config(**resolved_config)
            self.loaded_config = resolved_config
            return config
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}", "CONFIG_VALIDATION_ERROR")
    
    def _discover_config_files(self) -> List[str]:
        """Discover available configuration files."""
        discovered = []
        
        for config_file in self.config_files:
            file_path = self.config_dir / config_file
            if file_path.exists():
                discovered.append(str(file_path))
        
        if not discovered:
            raise ConfigurationError(
                f"No configuration files found in {self.config_dir}",
                "NO_CONFIG_FILES"
            )
        
        return discovered
    
    def _load_yaml_source(self, file_path: str):
        """Load YAML configuration source."""
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                return
            
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not isinstance(data, dict):
                raise ConfigurationError(f"Invalid YAML structure in {file_path}", "INVALID_YAML")
            
            # Determine priority based on file name
            priority = self._get_file_priority(file_path_obj.name)
            
            source = ConfigSource(
                path=str(file_path_obj),
                type='yaml',
                priority=priority,
                loaded=True,
                data=data
            )
            
            self.sources.append(source)
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML parsing error in {file_path}: {e}", "YAML_PARSE_ERROR")
        except Exception as e:
            raise ConfigurationError(f"Failed to load config file {file_path}: {e}", "FILE_LOAD_ERROR")
    
    def _get_file_priority(self, filename: str) -> int:
        """Get priority for configuration file."""
        # Lower numbers = higher priority
        priority_map = {
            'default.yaml': 100,
            'local.yaml': 50,
            'development.yaml': 30,
            'production.yaml': 20
        }
        return priority_map.get(filename, 60)
    
    def _load_environment_source(self):
        """Load environment variables as configuration source."""
        env_data = {}
        
        for key, value in os.environ.items():
            if key.startswith(self.env_prefix):
                # Convert MOC_SERVER_MAX_WORKERS to server.max_workers
                config_key = key[len(self.env_prefix):].lower()
                nested_keys = config_key.split('_')
                
                # Convert value to appropriate type
                converted_value = self._convert_env_value(value)
                
                # Set nested dictionary value
                self._set_nested_value(env_data, nested_keys, converted_value)
        
        if env_data:
            source = ConfigSource(
                path="environment_variables",
                type='env',
                priority=1,  # Highest priority
                loaded=True,
                data=env_data
            )
            self.sources.append(source)
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type."""
        # Boolean conversion
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Integer conversion
        if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
            return int(value)
        
        # Float conversion
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
        
        # JSON array/object conversion
        if value.startswith('[') or value.startswith('{'):
            try:
                import json
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Return as string
        return value
    
    def _set_nested_value(self, data: Dict[str, Any], keys: List[str], value: Any):
        """Set value in nested dictionary structure."""
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
    
    def _merge_sources(self) -> Dict[str, Any]:
        """Merge configuration sources by priority."""
        # Sort by priority (lower numbers first)
        sorted_sources = sorted(self.sources, key=lambda s: s.priority, reverse=True)
        
        merged = {}
        for source in sorted_sources:
            if source.loaded and source.data:
                merged = self._deep_merge(merged, source.data)
        
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in overlay.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _resolve_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variable placeholders in configuration."""
        def resolve_value(value: Any) -> Any:
            if isinstance(value, str):
                return self._substitute_env_vars(value)
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            else:
                return value
        
        return resolve_value(config)
    
    def _substitute_env_vars(self, text: str) -> str:
        """Substitute environment variables in text using ${VAR:default} syntax."""
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ""
            
            return os.environ.get(var_name, default_value)
        
        return re.sub(pattern, replace_match, text)
    
    def get_source_info(self) -> List[Dict[str, Any]]:
        """Get information about loaded configuration sources."""
        return [
            {
                'path': source.path,
                'type': source.type,
                'priority': source.priority,
                'loaded': source.loaded
            }
            for source in self.sources
        ]
    
    def get_effective_config(self) -> Optional[Dict[str, Any]]:
        """Get the effective merged configuration."""
        return self.loaded_config
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration structure."""
        required_sections = ['server', 'resources', 'models']
        
        for section in required_sections:
            if section not in config:
                raise ConfigurationError(f"Missing required section: {section}", "MISSING_SECTION")
        
        # Validate server section
        server_config = config.get('server', {})
        required_server_keys = ['zmq_port', 'grpc_port', 'rest_port', 'max_workers']
        
        for key in required_server_keys:
            if key not in server_config:
                raise ConfigurationError(f"Missing required server config: {key}", "MISSING_SERVER_CONFIG")
        
        return True
    
    def create_config_template(self, output_path: str):
        """Create a configuration file template."""
        template = {
            'title': 'ModelOpsCoordinatorConfig',
            'version': '1.0',
            'server': {
                'zmq_port': 7211,
                'grpc_port': 7212,
                'rest_port': 8008,
                'max_workers': 16
            },
            'resources': {
                'gpu_poll_interval': 5,
                'vram_soft_limit_mb': 22000,
                'eviction_threshold_pct': 90
            },
            'models': {
                'preload': [],
                'default_dtype': 'float16',
                'quantization': True
            },
            'learning': {
                'enable_auto_tune': True,
                'max_parallel_jobs': 2,
                'job_store': '${LEARNING_STORE:./learning_jobs.db}'
            },
            'goals': {
                'policy': 'priority_queue',
                'max_active_goals': 10
            },
            'resilience': {
                'circuit_breaker': {
                    'failure_threshold': 4,
                    'reset_timeout': 20
                },
                'bulkhead': {
                    'max_concurrent': 8,
                    'max_queue_size': 16
                }
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(template, f, default_flow_style=False, indent=2)


def load_config(config_file: Optional[str] = None, config_dir: str = "config") -> Config:
    """
    Convenience function to load configuration.
    
    Args:
        config_file: Optional specific config file
        config_dir: Configuration directory
        
    Returns:
        Loaded and validated Config object
    """
    loader = UnifiedConfigLoader(config_dir)
    return loader.load_config(config_file)