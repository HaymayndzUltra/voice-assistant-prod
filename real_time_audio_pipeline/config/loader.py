"""
Real-Time Audio Pipeline - Unified Configuration Loader

Comprehensive configuration loading system with environment variable substitution,
validation, and multi-environment support for the RTAP system.
"""

import logging
import os
import re
import socket
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml


class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class UnifiedConfigLoader:
    """
    Unified configuration loader for RTAP with advanced features.

    Features:
    - Environment variable substitution with defaults
    - Multi-environment configuration support (default, main_pc, pc2)
    - Configuration validation and type checking
    - Automatic hostname-based environment detection
    - Configuration merging and inheritance
    - Detailed logging and error reporting
    """

    def __init__(self, config_dir: Optional[Union[str, Path]] = None):
        """
        Initialize configuration loader.

        Args:
            config_dir: Directory containing configuration files (defaults to ./config)
        """
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self.logger = logging.getLogger(__name__)

        # Environment variable substitution pattern
        self.env_pattern = re.compile(r'\$\{([^}]+)\}')

        # Configuration cache
        self._config_cache: Dict[str, Any] = {}

        self.logger.debug(f"UnifiedConfigLoader initialized with config_dir: {self.config_dir}")

    def load_config(self,
                   environment: Optional[str] = None,
                   config_file: Optional[str] = None,
                   validate: bool = True) -> Dict[str, Any]:
        """
        Load and process configuration with environment variable substitution.

        Args:
            environment: Target environment (default, main_pc, pc2, or auto-detect)
            config_file: Specific config file to load (overrides environment)
            validate: Whether to validate the configuration

        Returns:
            Processed configuration dictionary

        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        try:
            # Determine configuration file
            if config_file:
                config_path = self.config_dir / config_file
            else:
                environment = environment or self._detect_environment()
                config_path = self.config_dir / f"{environment}.yaml"

            # Check if file exists
            if not config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {config_path}")

            self.logger.info(f"Loading configuration from: {config_path}")

            # Load YAML configuration
            with open(config_path, encoding='utf-8') as file:
                raw_config = yaml.safe_load(file)

            if not raw_config:
                raise ConfigurationError(f"Empty or invalid configuration file: {config_path}")

            # Process environment variable substitution
            processed_config = self._substitute_environment_variables(raw_config)

            # Apply configuration inheritance if not using default
            if environment != 'default' and not config_file:
                processed_config = self._apply_inheritance(processed_config, environment)

            # Validate configuration
            if validate:
                self._validate_configuration(processed_config)

            # Cache configuration
            cache_key = f"{environment or 'custom'}_{config_file or 'default'}"
            self._config_cache[cache_key] = processed_config

            self.logger.info(f"Configuration loaded successfully: {processed_config.get('title', 'Unknown')}")

            return processed_config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML parsing error: {e}")
        except Exception as e:
            raise ConfigurationError(f"Configuration loading failed: {e}")

    def _detect_environment(self) -> str:
        """
        Automatically detect environment based on hostname and available configurations.

        Returns:
            Environment name (default, main_pc, pc2)
        """
        try:
            hostname = socket.gethostname().lower()

            # Check for specific hostname patterns
            if 'main' in hostname or 'primary' in hostname:
                env = 'main_pc'
            elif 'pc2' in hostname or 'secondary' in hostname or '2' in hostname:
                env = 'pc2'
            else:
                env = 'default'

            # Verify the configuration file exists
            config_path = self.config_dir / f"{env}.yaml"
            if not config_path.exists():
                self.logger.warning(f"Environment config {env}.yaml not found, falling back to default")
                env = 'default'

            self.logger.info(f"Auto-detected environment: {env} (hostname: {hostname})")
            return env

        except Exception as e:
            self.logger.warning(f"Environment detection failed: {e}, using default")
            return 'default'

    def _substitute_environment_variables(self, config: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.

        Supports format: ${VARIABLE_NAME:default_value}

        Args:
            config: Configuration object (dict, list, or string)

        Returns:
            Configuration with environment variables substituted
        """
        if isinstance(config, dict):
            return {key: self._substitute_environment_variables(value)
                   for key, value in config.items()}

        elif isinstance(config, list):
            return [self._substitute_environment_variables(item) for item in config]

        elif isinstance(config, str):
            return self._substitute_string_variables(config)

        else:
            return config

    def _substitute_string_variables(self, text: str) -> Union[str, int, float, bool]:
        """
        Substitute environment variables in a string.

        Args:
            text: String potentially containing environment variables

        Returns:
            String with variables substituted, with type conversion
        """
        def replace_var(match):
            var_spec = match.group(1)

            # Parse variable name and default value
            if ':' in var_spec:
                var_name, default_value = var_spec.split(':', 1)
            else:
                var_name, default_value = var_spec, ''

            # Get environment variable value
            env_value = os.environ.get(var_name, default_value)

            self.logger.debug(f"Environment substitution: {var_name} = {env_value}")

            return env_value

        # Perform substitution
        result = self.env_pattern.sub(replace_var, text)

        # Attempt type conversion for common types
        return self._convert_type(result)

    def _convert_type(self, value: str) -> Union[str, int, float, bool]:
        """
        Convert string values to appropriate Python types.

        Args:
            value: String value to convert

        Returns:
            Value converted to appropriate type
        """
        if not isinstance(value, str):
            return value

        # Boolean conversion
        if value.lower() in ('true', 'yes', 'on', '1'):
            return True
        elif value.lower() in ('false', 'no', 'off', '0'):
            return False

        # Numeric conversion
        try:
            if '.' in value or 'e' in value.lower():
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass

        # Return as string if no conversion possible
        return value

    def _apply_inheritance(self, config: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """
        Apply configuration inheritance from default.yaml.

        Args:
            config: Environment-specific configuration
            environment: Environment name

        Returns:
            Merged configuration with defaults
        """
        try:
            # Load default configuration
            default_path = self.config_dir / "default.yaml"
            if default_path.exists():
                with open(default_path, encoding='utf-8') as file:
                    default_config = yaml.safe_load(file)

                # Apply environment variable substitution to defaults
                default_config = self._substitute_environment_variables(default_config)

                # Merge configurations (environment overrides default)
                merged_config = self._deep_merge(default_config, config)

                self.logger.debug(f"Applied configuration inheritance for {environment}")
                return merged_config
            else:
                self.logger.warning("default.yaml not found, skipping inheritance")
                return config

        except Exception as e:
            self.logger.error(f"Configuration inheritance failed: {e}")
            return config

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two configuration dictionaries.

        Args:
            base: Base configuration dictionary
            override: Override configuration dictionary

        Returns:
            Merged configuration dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_configuration(self, config: Dict[str, Any]) -> None:
        """
        Validate configuration structure and required fields.

        Args:
            config: Configuration dictionary to validate

        Raises:
            ConfigurationError: If validation fails
        """
        required_sections = ['audio', 'output']
        required_audio_fields = ['sample_rate', 'frame_ms', 'channels']
        required_output_fields = ['zmq_pub_port_events', 'zmq_pub_port_transcripts', 'websocket_port']

        # Check required sections
        for section in required_sections:
            if section not in config:
                raise ConfigurationError(f"Required configuration section missing: {section}")

        # Validate audio section
        audio_config = config['audio']
        for field in required_audio_fields:
            if field not in audio_config:
                raise ConfigurationError(f"Required audio field missing: {field}")

        # Validate audio parameters
        sample_rate = audio_config['sample_rate']
        if not isinstance(sample_rate, int) or sample_rate < 8000 or sample_rate > 48000:
            raise ConfigurationError(f"Invalid sample_rate: {sample_rate}")

        frame_ms = audio_config['frame_ms']
        if not isinstance(frame_ms, int) or frame_ms < 10 or frame_ms > 100:
            raise ConfigurationError(f"Invalid frame_ms: {frame_ms}")

        # Validate output section
        output_config = config['output']
        for field in required_output_fields:
            if field not in output_config:
                raise ConfigurationError(f"Required output field missing: {field}")

        # Validate port numbers
        for port_field in ['zmq_pub_port_events', 'zmq_pub_port_transcripts', 'websocket_port']:
            port = output_config[port_field]
            if not isinstance(port, int) or port < 1024 or port > 65535:
                raise ConfigurationError(f"Invalid port number for {port_field}: {port}")

        self.logger.debug("Configuration validation passed")

    def get_cached_config(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached configuration.

        Args:
            cache_key: Cache key for the configuration

        Returns:
            Cached configuration or None if not found
        """
        return self._config_cache.get(cache_key)

    def list_available_configs(self) -> list:
        """
        List available configuration files.

        Returns:
            List of available configuration file names
        """
        config_files = []
        for file_path in self.config_dir.glob("*.yaml"):
            config_files.append(file_path.stem)

        return sorted(config_files)

    def validate_environment_variables(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract and validate all environment variables referenced in configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary of environment variables and their current values
        """
        env_vars = {}

        def extract_env_vars(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    extract_env_vars(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_env_vars(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                matches = self.env_pattern.findall(obj)
                for match in matches:
                    var_name = match.split(':')[0] if ':' in match else match
                    env_vars[var_name] = {
                        'value': os.environ.get(var_name, 'NOT_SET'),
                        'used_in': path,
                        'full_spec': match
                    }

        extract_env_vars(config)
        return env_vars


# Convenience functions for common usage patterns

def load_default_config() -> Dict[str, Any]:
    """Load default configuration with automatic environment detection."""
    loader = UnifiedConfigLoader()
    return loader.load_config()


def load_config_for_environment(environment: str) -> Dict[str, Any]:
    """Load configuration for specific environment."""
    loader = UnifiedConfigLoader()
    return loader.load_config(environment=environment)


def load_config_with_overrides(**overrides) -> Dict[str, Any]:
    """Load default configuration with runtime overrides."""
    config = load_default_config()

    # Apply overrides
    for key, value in overrides.items():
        if '.' in key:
            # Handle nested keys like 'audio.sample_rate'
            keys = key.split('.')
            current = config
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
        else:
            config[key] = value

    return config
