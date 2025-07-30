#!/usr/bin/env python3
"""
Secure Secret Manager for AI Agent System
Phase 0 Day 5 - Task 5B

This module provides secure secret access avoiding process list exposure.
Implements multi-source secret resolution with proper fallback hierarchy.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Union

logger = logging.getLogger(__name__)


class SecretNotFoundError(Exception):
    """Raised when a required secret cannot be found in any configured source."""


class SecretValidationError(Exception):
    """Raised when a secret fails validation checks."""


class SecretManager:
    """
    Secure secret access manager avoiding process list exposure.
    
    Resolution order:
    1. Environment Variables (production)
    2. Secure file location (/run/secrets/ - containers/production)
    3. Development file location (./secrets/ - local development)
    4. ERROR: No hardcoded fallbacks allowed
    """
    
    # Standard secret locations
    CONTAINER_SECRETS_DIR = Path("/run/secrets")
    DEV_SECRETS_DIR = Path("secrets")
    
    def __init__(self, 
                 dev_secrets_dir: Optional[Union[str, Path]] = None,
                 container_secrets_dir: Optional[Union[str, Path]] = None,
                 allow_env_vars: bool = True,
                 strict_mode: bool = False):
        """
        Initialize SecretManager.
        
        Args:
            dev_secrets_dir: Custom development secrets directory
            container_secrets_dir: Custom container secrets directory  
            allow_env_vars: Whether to check environment variables
            strict_mode: If True, fail fast on any secret access error
        """
        self.dev_secrets_dir = Path(dev_secrets_dir) if dev_secrets_dir else self.DEV_SECRETS_DIR
        self.container_secrets_dir = Path(container_secrets_dir) if container_secrets_dir else self.CONTAINER_SECRETS_DIR
        self.allow_env_vars = allow_env_vars
        self.strict_mode = strict_mode
        
        # Secret cache for performance (optional)
        self._secret_cache: Dict[str, str] = {}
        self._cache_enabled = False
        
        logger.debug(f"SecretManager initialized - dev: {self.dev_secrets_dir}, "
                    f"container: {self.container_secrets_dir}, env_vars: {allow_env_vars}")
    
    @staticmethod
    def get_secret(secret_name: str, required: bool = True) -> str:
        """
        Get secret from secure storage (env var, file, or vault).
        
        Args:
            secret_name: Name of the secret to retrieve
            required: If True, raise exception when secret not found
            
        Returns:
            Secret value as string
            
        Raises:
            SecretNotFoundError: When required secret is not found
        """
        # Create default instance for static method
        manager = SecretManager()
        return manager.get_secret_value(secret_name, required=required)
    
    def get_secret_value(self, secret_name: str, required: bool = True) -> str:
        """
        Get secret value with full resolution logic.
        
        Args:
            secret_name: Name of the secret to retrieve
            required: If True, raise exception when secret not found
            
        Returns:
            Secret value as string
            
        Raises:
            SecretNotFoundError: When required secret is not found
        """
        logger.debug(f"Resolving secret: {secret_name}")
        
        # Check cache first (if enabled)
        if self._cache_enabled and secret_name in self._secret_cache:
            logger.debug(f"Secret {secret_name} found in cache")
            return self._secret_cache[secret_name]
        
        # 1. Try environment variable first
        if self.allow_env_vars:
            env_value = os.getenv(secret_name)
            if env_value:
                logger.debug(f"Secret {secret_name} found in environment variables")
                self._cache_secret(secret_name, env_value)
                return env_value
        
        # 2. Try secure file location (containers/production)
        container_secret = self._read_secret_file(self.container_secrets_dir / secret_name)
        if container_secret:
            logger.debug(f"Secret {secret_name} found in container secrets directory")
            self._cache_secret(secret_name, container_secret)
            return container_secret
        
        # 3. Try development file location  
        dev_secret = self._read_secret_file(self.dev_secrets_dir / secret_name)
        if dev_secret:
            logger.debug(f"Secret {secret_name} found in development secrets directory")
            self._cache_secret(secret_name, dev_secret)
            return dev_secret
        
        # 4. Secret not found - handle based on required flag
        if required:
            error_msg = (f"Secret '{secret_name}' not found in any secure location. "
                        f"Checked: environment{',' if self.allow_env_vars else ' (disabled),'} "
                        f"{self.container_secrets_dir}, {self.dev_secrets_dir}")
            logger.error(error_msg)
            raise SecretNotFoundError(error_msg)
        else:
            logger.warning(f"Optional secret '{secret_name}' not found")
            return ""
    
    def _read_secret_file(self, secret_path: Path) -> Optional[str]:
        """
        Read secret from file with proper error handling.
        
        Args:
            secret_path: Path to secret file
            
        Returns:
            Secret content or None if not found/readable
        """
        try:
            if secret_path.exists() and secret_path.is_file():
                # Check file permissions for security
                stat = secret_path.stat()
                if stat.st_mode & 0o077:  # Check for group/other permissions
                    logger.warning(f"Secret file {secret_path} has overly permissive permissions")
                
                content = secret_path.read_text().strip()
                if content:
                    return content
                else:
                    logger.warning(f"Secret file {secret_path} is empty")
                    
        except PermissionError:
            logger.warning(f"Permission denied reading secret file: {secret_path}")
        except Exception as e:
            logger.warning(f"Error reading secret file {secret_path}: {e}")
            if self.strict_mode:
                raise SecretValidationError(f"Failed to read secret file {secret_path}: {e}")
        
        return None
    
    def _cache_secret(self, secret_name: str, secret_value: str):
        """Cache secret value if caching is enabled."""
        if self._cache_enabled:
            self._secret_cache[secret_name] = secret_value
    
    def enable_caching(self, enabled: bool = True):
        """Enable or disable secret caching for performance."""
        self._cache_enabled = enabled
        if not enabled:
            self._secret_cache.clear()
        logger.debug(f"Secret caching {'enabled' if enabled else 'disabled'}")
    
    def clear_cache(self):
        """Clear all cached secrets."""
        self._secret_cache.clear()
        logger.debug("Secret cache cleared")
    
    @staticmethod
    def get_nats_credentials() -> Tuple[str, str]:
        """
        Get NATS username and password securely.
        
        Returns:
            Tuple of (username, password)
            
        Raises:
            SecretNotFoundError: When NATS credentials not found
        """
        manager = SecretManager()
        username = manager.get_secret_value("NATS_USERNAME")
        password = manager.get_secret_value("NATS_PASSWORD")
        return username, password
    
    @staticmethod
    def get_redis_credentials() -> Tuple[str, int, Optional[str]]:
        """
        Get Redis connection details securely.
        
        Returns:
            Tuple of (host, port, password)
        """
        manager = SecretManager()
        host = manager.get_secret_value("REDIS_HOST", required=False) or "localhost"
        port_str = manager.get_secret_value("REDIS_PORT", required=False) or "6379"
        password = manager.get_secret_value("REDIS_PASSWORD", required=False)
        
        try:
            port = int(port_str)
        except ValueError:
            logger.warning(f"Invalid Redis port '{port_str}', using default 6379")
            port = 6379
        
        return host, port, password
    
    @staticmethod
    def get_jwt_secret(service_name: str = "") -> str:
        """
        Get JWT secret for authentication.
        
        Args:
            service_name: Service-specific JWT secret name
            
        Returns:
            JWT secret string
        """
        manager = SecretManager()
        
        # Try service-specific secret first
        if service_name:
            service_secret_name = f"JWT_SECRET_{service_name.upper()}"
            try:
                return manager.get_secret_value(service_secret_name)
            except SecretNotFoundError:
                logger.debug(f"Service-specific JWT secret {service_secret_name} not found, trying default")
        
        # Fall back to default JWT secret
        return manager.get_secret_value("JWT_SECRET")
    
    @staticmethod
    def get_api_token(service_name: str) -> str:
        """
        Get API token for external service authentication.
        
        Args:
            service_name: Name of the service (e.g., "PHI_TRANSLATOR")
            
        Returns:
            API token string
        """
        manager = SecretManager()
        token_name = f"{service_name.upper()}_TOKEN"
        return manager.get_secret_value(token_name)
    
    def validate_secret_setup(self) -> Dict[str, bool]:
        """
        Validate that secret management infrastructure is properly configured.
        
        Returns:
            Dictionary with validation results
        """
        results = {
            "env_vars_enabled": self.allow_env_vars,
            "dev_secrets_dir_exists": self.dev_secrets_dir.exists(),
            "dev_secrets_dir_writable": False,
            "container_secrets_dir_exists": self.container_secrets_dir.exists(),
            "container_secrets_dir_readable": False,
        }
        
        # Check dev secrets directory
        if results["dev_secrets_dir_exists"]:
            try:
                test_file = self.dev_secrets_dir / ".write_test"
                test_file.write_text("test")
                test_file.unlink()
                results["dev_secrets_dir_writable"] = True
            except Exception:
                pass
        
        # Check container secrets directory
        if results["container_secrets_dir_exists"]:
            try:
                list(self.container_secrets_dir.iterdir())
                results["container_secrets_dir_readable"] = True
            except Exception:
                pass
        
        return results
    
    def list_available_secrets(self) -> Dict[str, List[str]]:
        """
        List all available secrets by source (for debugging/administration).
        
        Returns:
            Dictionary mapping source to list of secret names
        """
        secrets = {
            "environment_variables": [],
            "container_secrets": [],
            "dev_secrets": []
        }
        
        # Environment variables (only check for common secret patterns)
        if self.allow_env_vars:
            env_patterns = ["_TOKEN", "_SECRET", "_PASSWORD", "_KEY", "NATS_", "REDIS_", "JWT_"]
            for env_var in os.environ:
                if any(pattern in env_var for pattern in env_patterns):
                    secrets["environment_variables"].append(env_var)
        
        # Container secrets
        if self.container_secrets_dir.exists():
            try:
                secrets["container_secrets"] = [
                    f.name for f in self.container_secrets_dir.iterdir() 
                    if f.is_file() and not f.name.startswith('.')
                ]
            except Exception as e:
                logger.warning(f"Error listing container secrets: {e}")
        
        # Development secrets
        if self.dev_secrets_dir.exists():
            try:
                secrets["dev_secrets"] = [
                    f.name for f in self.dev_secrets_dir.iterdir() 
                    if f.is_file() and not f.name.startswith('.')
                ]
            except Exception as e:
                logger.warning(f"Error listing dev secrets: {e}")
        
        return secrets


class SecretInjector:
    """Helper class for secure secret injection into configuration and environment."""
    
    def __init__(self, secret_manager: Optional[SecretManager] = None):
        self.secret_manager = secret_manager or SecretManager()
    
    def inject_secrets_into_env(self, secret_mapping: Dict[str, str]):
        """
        Inject secrets into environment variables.
        
        Args:
            secret_mapping: Dict mapping env var names to secret names
        """
        for env_var, secret_name in secret_mapping.items():
            try:
                secret_value = self.secret_manager.get_secret_value(secret_name)
                os.environ[env_var] = secret_value
                logger.debug(f"Injected secret {secret_name} into env var {env_var}")
            except SecretNotFoundError as e:
                logger.error(f"Failed to inject secret {secret_name}: {e}")
                raise
    
    def resolve_secret_placeholders(self, text: str) -> str:
        """
        Resolve ${SECRET_NAME} placeholders in text with actual secret values.
        
        Args:
            text: Text containing secret placeholders
            
        Returns:
            Text with placeholders resolved to actual secret values
        """
        import re
        
        # Find all ${SECRET_NAME} patterns
        pattern = r'\$\{([A-Z_]+)\}'
        matches = re.findall(pattern, text)
        
        resolved_text = text
        for secret_name in matches:
            try:
                secret_value = self.secret_manager.get_secret_value(secret_name)
                placeholder = f"${{{secret_name}}}"
                resolved_text = resolved_text.replace(placeholder, secret_value)
                logger.debug(f"Resolved placeholder {placeholder}")
            except SecretNotFoundError as e:
                logger.error(f"Failed to resolve placeholder {placeholder}: {e}")
                raise
        
        return resolved_text


# Convenience functions for common use cases
def get_secret(secret_name: str, required: bool = True) -> str:
    """Convenience function to get a secret using default SecretManager."""
    return SecretManager.get_secret(secret_name, required)


def get_nats_url() -> str:
    """Get complete NATS URL with credentials."""
    username, password = SecretManager.get_nats_credentials()
    host = get_secret("NATS_HOST", required=False) or "localhost"
    port = get_secret("NATS_PORT", required=False) or "4222"
    return f"nats://{username}:{password}@{host}:{port}"


def get_redis_url() -> str:
    """Get complete Redis URL with credentials."""
    host, port, password = SecretManager.get_redis_credentials()
    if password:
        return f"redis://:{password}@{host}:{port}/0"
    else:
        return f"redis://{host}:{port}/0"


# Development helper functions
def create_dev_secrets_template():
    """Create template secrets directory for development."""
    secrets_dir = Path("secrets")
    secrets_dir.mkdir(exist_ok=True)
    
    # Create template secret files
    template_secrets = {
        "NATS_USERNAME": "admin",
        "NATS_PASSWORD": "dev_password_change_in_prod",
        "REDIS_PASSWORD": "dev_redis_password",
        "JWT_SECRET": "dev_jwt_secret_change_in_production",
        "PHI_TRANSLATOR_TOKEN": "dev_translator_token"
    }
    
    for secret_name, default_value in template_secrets.items():
        secret_file = secrets_dir / secret_name
        if not secret_file.exists():
            secret_file.write_text(default_value)
            secret_file.chmod(0o600)  # Secure permissions
            logger.info(f"Created template secret: {secret_file}")
    
    # Create .gitignore to exclude secrets
    gitignore_file = Path(".gitignore")
    gitignore_content = "secrets/\n"
    
    if gitignore_file.exists():
        existing_content = gitignore_file.read_text()
        if "secrets/" not in existing_content:
            gitignore_file.write_text(existing_content + gitignore_content)
            logger.info("Added secrets/ to .gitignore")
    else:
        gitignore_file.write_text(gitignore_content)
        logger.info("Created .gitignore with secrets/ exclusion")


if __name__ == "__main__":
    # Example usage and testing
    print("SecretManager Test")
    print("=" * 50)
    
    # Initialize secret manager
    manager = SecretManager()
    
    # Validate setup
    validation = manager.validate_secret_setup()
    print("Setup validation:")
    for key, value in validation.items():
        print(f"  {key}: {'✅' if value else '❌'}")
    
    # List available secrets
    available = manager.list_available_secrets()
    print("\nAvailable secrets:")
    for source, secrets in available.items():
        print(f"  {source}: {len(secrets)} secrets")
        for secret in secrets[:3]:  # Show first 3
            print(f"    - {secret}")
        if len(secrets) > 3:
            print(f"    ... and {len(secrets) - 3} more")
    
    # Test secret resolution (safe examples)
    try:
        # This will fail in most cases, which is expected
        test_secret = manager.get_secret_value("TEST_SECRET", required=False)
        print(f"\nTest secret: {'Found' if test_secret else 'Not found'}")
    except Exception as e:
        print(f"\nTest secret resolution: {e}")
    
    print("\n✅ SecretManager module loaded successfully") 