#!/usr/bin/env python3
"""
Environment Variable Standardizer v3

Provides standardized environment variable access with fallback mapping.
Implements the Blueprint.md Step 4: Environment Variable Standardization.

Standard Variables:
- MAINPC_IP (replaces MAIN_PC_IP)
- PC2_IP (consistent)
- MACHINE_TYPE (replaces MACHINE_ROLE)

Features:
- Automatic fallback for legacy variable names
- Type conversion and validation
- Caching for performance
- Docker/container awareness
- Cross-machine coordination support
"""

import os
import logging
import warnings
from typing import Dict, Any, Union, List, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class EnvVarSpec:
    """Specification for an environment variable"""
    name: str
    default: Any
    type_converter: Callable[[str], Any]
    legacy_names: List[str]
    description: str
    docker_aware: bool = False

class EnvStandardizer:
    """
    Centralized environment variable standardizer with fallback support.
    
    This class ensures consistent environment variable usage across the entire codebase
    while maintaining backward compatibility with legacy variable names.
    """
    
    # Standardized environment variable specifications
    _ENV_SPECS: Dict[str, EnvVarSpec] = {
        # Machine identification
        "MACHINE_TYPE": EnvVarSpec(
            name="MACHINE_TYPE",
            default="mainpc",
            type_converter=lambda x: x.lower(),
            legacy_names=["MACHINE_ROLE", "MACHINE_NAME"],
            description="Machine type: mainpc or pc2",
            docker_aware=True
        ),
        
        # Network configuration - IP addresses
        "MAINPC_IP": EnvVarSpec(
            name="MAINPC_IP", 
            default="localhost",
            type_converter=str,
            legacy_names=["MAIN_PC_IP", "MAINPC_HOST", "MAIN_PC_HOST"],
            description="MainPC IP address for cross-machine communication",
            docker_aware=True
        ),
        
        "PC2_IP": EnvVarSpec(
            name="PC2_IP",
            default="localhost", 
            type_converter=str,
            legacy_names=["PC2_HOST"],
            description="PC2 IP address for cross-machine communication",
            docker_aware=True
        ),
        
        # Network configuration - binding
        "BIND_ADDRESS": EnvVarSpec(
            name="BIND_ADDRESS",
            default="0.0.0.0",
            type_converter=str,
            legacy_names=["BIND_IP", "LISTEN_ADDRESS"],
            description="Address to bind services to",
            docker_aware=True
        ),
        
        # Service discovery
        "SERVICE_REGISTRY_HOST": EnvVarSpec(
            name="SERVICE_REGISTRY_HOST",
            default="localhost",
            type_converter=str,
            legacy_names=["REGISTRY_HOST", "SERVICE_DISCOVERY_HOST"],
            description="Service registry host address",
            docker_aware=True
        ),
        
        "SERVICE_REGISTRY_PORT": EnvVarSpec(
            name="SERVICE_REGISTRY_PORT",
            default=7100,
            type_converter=int,
            legacy_names=["REGISTRY_PORT", "SERVICE_DISCOVERY_PORT"],
            description="Service registry port",
        ),
        
        # Docker/container environment
        "CONTAINER_MODE": EnvVarSpec(
            name="CONTAINER_MODE",
            default=False,
            type_converter=lambda x: x.lower() in ('true', '1', 'yes', 'on'),
            legacy_names=["DOCKER_MODE", "IN_CONTAINER"],
            description="Whether running in a container",
            docker_aware=True
        ),
        
        # Security settings
        "SECURE_ZMQ": EnvVarSpec(
            name="SECURE_ZMQ",
            default=False,
            type_converter=lambda x: x.lower() in ('true', '1', 'yes', 'on'),
            legacy_names=["ENABLE_SECURE_ZMQ", "ZMQ_SECURITY"],
            description="Enable ZMQ security (CURVE)",
        ),
        
        # Resource limits
        "MAX_MEMORY_MB": EnvVarSpec(
            name="MAX_MEMORY_MB", 
            default=2048,
            type_converter=int,
            legacy_names=["MEMORY_LIMIT", "MAX_RAM_MB"],
            description="Maximum memory usage in MB",
        ),
        
        "MAX_VRAM_MB": EnvVarSpec(
            name="MAX_VRAM_MB",
            default=2048,
            type_converter=int, 
            legacy_names=["VRAM_LIMIT", "GPU_MEMORY_LIMIT"],
            description="Maximum VRAM usage in MB",
        ),
        
        # Timeouts and retries
        "ZMQ_REQUEST_TIMEOUT": EnvVarSpec(
            name="ZMQ_REQUEST_TIMEOUT",
            default=5000,
            type_converter=int,
            legacy_names=["REQUEST_TIMEOUT", "ZMQ_TIMEOUT"],
            description="ZMQ request timeout in milliseconds",
        ),
        
        "CONNECTION_RETRIES": EnvVarSpec(
            name="CONNECTION_RETRIES",
            default=3,
            type_converter=int,
            legacy_names=["MAX_RETRIES", "RETRY_COUNT"],
            description="Maximum connection retry attempts",
        ),
        
        # Logging
        "LOG_LEVEL": EnvVarSpec(
            name="LOG_LEVEL",
            default="INFO",
            type_converter=str.upper,
            legacy_names=["LOGGING_LEVEL"],
            description="Logging level (DEBUG, INFO, WARNING, ERROR)",
        ),
        
        # Environment type
        "ENV_TYPE": EnvVarSpec(
            name="ENV_TYPE",
            default="development",
            type_converter=str.lower,
            legacy_names=["ENVIRONMENT", "DEPLOY_ENV"],
            description="Environment type (development, production, testing)",
        ),
    }
    
    # Cache for resolved values
    _cache: Dict[str, Any] = {}
    
    @classmethod
    def get(cls, var_name: str, default: Any = None) -> Any:
        """
        Get a standardized environment variable value with fallback support.
        
        Args:
            var_name: Standard variable name
            default: Override default value
            
        Returns:
            Variable value with proper type conversion
        """
        # Check cache first
        cache_key = f"{var_name}:{default}"
        if cache_key in cls._cache:
            return cls._cache[cache_key]
        
        # Get specification
        spec = cls._ENV_SPECS.get(var_name)
        if not spec:
            # Unknown variable, return as-is from environment
            value = os.environ.get(var_name, default)
            cls._cache[cache_key] = value
            return value
        
        # Try standard name first
        raw_value = os.environ.get(spec.name)
        
        # Try legacy names if standard not found
        if raw_value is None:
            for legacy_name in spec.legacy_names:
                raw_value = os.environ.get(legacy_name)
                if raw_value is not None:
                    # Issue deprecation warning
                    warnings.warn(
                        f"Environment variable '{legacy_name}' is deprecated. "
                        f"Use '{spec.name}' instead.",
                        DeprecationWarning,
                        stacklevel=3
                    )
                    logger.debug(f"Using legacy env var {legacy_name} -> {spec.name}")
                    break
        
        # Use default if still not found
        if raw_value is None:
            raw_value = default if default is not None else spec.default
        
        # Convert type
        try:
            if raw_value is None:
                value = None
            elif isinstance(raw_value, str):
                value = spec.type_converter(raw_value)
            else:
                value = raw_value
        except (ValueError, TypeError) as e:
            logger.warning(f"Error converting {var_name}='{raw_value}': {e}")
            value = spec.default
        
        # Apply Docker-aware logic
        if spec.docker_aware and cls.is_docker_environment():
            value = cls._apply_docker_awareness(var_name, value)
        
        # Cache and return
        cls._cache[cache_key] = value
        return value
    
    @classmethod
    def is_docker_environment(cls) -> bool:
        """Check if running in a Docker container."""
        return (
            os.path.exists('/.dockerenv') or
            os.environ.get('CONTAINER_MODE', '').lower() in ('true', '1', 'yes') or
            os.environ.get('DOCKER_MODE', '').lower() in ('true', '1', 'yes')
        )
    
    @classmethod
    def _apply_docker_awareness(cls, var_name: str, value: Any) -> Any:
        """Apply Docker-specific logic to environment variables."""
        if var_name in ("MAINPC_IP", "PC2_IP", "SERVICE_REGISTRY_HOST"):
            # In Docker, localhost becomes service names
            if value == "localhost":
                if var_name == "MAINPC_IP":
                    return "mainpc-service"
                elif var_name == "PC2_IP": 
                    return "pc2-service"
                elif var_name == "SERVICE_REGISTRY_HOST":
                    return "service-registry"
        elif var_name == "MACHINE_TYPE":
            # Check for Docker service name hints
            hostname = os.environ.get("HOSTNAME", "")
            if "mainpc" in hostname.lower():
                return "mainpc"
            elif "pc2" in hostname.lower():
                return "pc2"
        
        return value
    
    @classmethod
    def get_machine_ip(cls, machine: str) -> str:
        """
        Get IP address for a specific machine.
        
        Args:
            machine: Machine name ('mainpc' or 'pc2')
            
        Returns:
            IP address string
        """
        machine = machine.lower()
        if machine == "mainpc":
            return cls.get("MAINPC_IP")
        elif machine == "pc2":
            return cls.get("PC2_IP")
        else:
            logger.warning(f"Unknown machine: {machine}")
            return "localhost"
    
    @classmethod
    def get_current_machine(cls) -> str:
        """Get the current machine type."""
        machine_type = cls.get("MACHINE_TYPE")
        return machine_type.lower() if machine_type else "mainpc"
    
    @classmethod
    def is_cross_machine_setup(cls) -> bool:
        """Check if this is a cross-machine setup (not all localhost)."""
        mainpc_ip = cls.get("MAINPC_IP")
        pc2_ip = cls.get("PC2_IP")
        return not (mainpc_ip in ("localhost", "127.0.0.1") and pc2_ip in ("localhost", "127.0.0.1"))
    
    @classmethod
    def get_service_address(cls, service_host: str, service_port: Union[int, str]) -> str:
        """
        Build a service address from host and port.
        
        Args:
            service_host: Host name or IP
            service_port: Port number
            
        Returns:
            Full service address (tcp://host:port)
        """
        return f"tcp://{service_host}:{service_port}"
    
    @classmethod
    def get_all_standardized(cls) -> Dict[str, Any]:
        """Get all standardized environment variables with their current values."""
        result = {}
        for var_name in cls._ENV_SPECS:
            result[var_name] = cls.get(var_name)
        return result
    
    @classmethod
    def export_for_subprocess(cls) -> Dict[str, str]:
        """Get environment variables suitable for subprocess.Popen(env=...)."""
        env = os.environ.copy()
        
        # Add all standardized variables
        for var_name in cls._ENV_SPECS:
            value = cls.get(var_name)
            if value is not None:
                env[var_name] = str(value)
        
        return env
    
    @classmethod
    def validate_configuration(cls) -> List[str]:
        """
        Validate current environment configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check machine type
        machine_type = cls.get("MACHINE_TYPE")
        if machine_type not in ("mainpc", "pc2"):
            errors.append(f"Invalid MACHINE_TYPE: {machine_type}. Must be 'mainpc' or 'pc2'")
        
        # Check IP addresses
        mainpc_ip = cls.get("MAINPC_IP")
        pc2_ip = cls.get("PC2_IP")
        
        if not mainpc_ip:
            errors.append("MAINPC_IP is required")
        if not pc2_ip:
            errors.append("PC2_IP is required")
        
        # Check for invalid IP formats (basic validation)
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$|^localhost$|^[\w\-\.]+$'
        
        if mainpc_ip and not re.match(ip_pattern, mainpc_ip):
            errors.append(f"Invalid MAINPC_IP format: {mainpc_ip}")
        if pc2_ip and not re.match(ip_pattern, pc2_ip):
            errors.append(f"Invalid PC2_IP format: {pc2_ip}")
        
        # Check resource limits
        max_memory = cls.get("MAX_MEMORY_MB")
        if max_memory < 512:
            errors.append(f"MAX_MEMORY_MB too low: {max_memory}MB (minimum 512MB)")
        
        return errors
    
    @classmethod
    def clear_cache(cls):
        """Clear the environment variable cache."""
        cls._cache.clear()
    
    @classmethod
    def get_legacy_mapping(cls) -> Dict[str, str]:
        """Get mapping of legacy variable names to standard names."""
        mapping = {}
        for spec in cls._ENV_SPECS.values():
            for legacy_name in spec.legacy_names:
                mapping[legacy_name] = spec.name
        return mapping

# Convenience functions for common operations
def get_env(var_name: str, default: Any = None) -> Any:
    """Get a standardized environment variable (convenience function)."""
    return EnvStandardizer.get(var_name, default)

def get_mainpc_ip() -> str:
    """Get MainPC IP address."""
    return EnvStandardizer.get("MAINPC_IP")

def get_pc2_ip() -> str:
    """Get PC2 IP address."""
    return EnvStandardizer.get("PC2_IP")

def get_machine_ip(machine: str) -> str:
    """Get IP address for a specific machine."""
    return EnvStandardizer.get_machine_ip(machine)

def get_current_machine() -> str:
    """Get current machine type."""
    return EnvStandardizer.get_current_machine()

def is_docker_environment() -> bool:
    """Check if running in Docker."""
    return EnvStandardizer.is_docker_environment()

def is_cross_machine_setup() -> bool:
    """Check if this is a cross-machine setup."""
    return EnvStandardizer.is_cross_machine_setup()

def build_service_address(service_host: str, service_port: Union[int, str]) -> str:
    """Build a TCP service address."""
    return EnvStandardizer.get_service_address(service_host, service_port)

def validate_env_config() -> List[str]:
    """Validate environment configuration."""
    return EnvStandardizer.validate_configuration()

# Legacy compatibility - these functions provide fallback support
def get_legacy_env(legacy_name: str, default: Any = None) -> Any:
    """Get environment variable by legacy name with automatic mapping."""
    mapping = EnvStandardizer.get_legacy_mapping()
    standard_name = mapping.get(legacy_name, legacy_name)
    return EnvStandardizer.get(standard_name, default) 