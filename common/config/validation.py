#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Configuration Validation & Schema - Phase 2.4

JSON Schema-based configuration validation system with environment-aware
validation rules, custom validators, and detailed error reporting.

Part of Phase 2.4: Configuration Validation & Schema - O3 Roadmap Implementation
"""

import json
import logging
import re
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft7Validator
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    ValidationError = Exception

# Fallback validation using built-in types
from .unified_config_manager import Config


class ValidationLevel(Enum):
    """Validation strictness levels."""
    STRICT = "strict"      # All validations must pass
    MODERATE = "moderate"  # Warnings for non-critical failures
    LENIENT = "lenient"    # Only critical validations required


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    schema_errors: List[str] = None
    custom_errors: List[str] = None
    
    def __bool__(self) -> bool:
        return self.valid
    
    def get_all_issues(self) -> List[str]:
        """Get all issues (errors + warnings)."""
        issues = []
        issues.extend(self.errors)
        issues.extend(self.warnings)
        if self.schema_errors:
            issues.extend(self.schema_errors)
        if self.custom_errors:
            issues.extend(self.custom_errors)
        return issues


class ConfigValidator:
    """Configuration validation engine with schema support."""
    
    def __init__(self, schema_dir: Optional[Path] = None, level: ValidationLevel = ValidationLevel.MODERATE):
        self.schema_dir = schema_dir or Path(__file__).parent / "schemas"
        self.level = level
        self.logger = logging.getLogger("config.validator")
        self.custom_validators: Dict[str, Callable] = {}
        self.schema_cache: Dict[str, Dict] = {}
        
        # Initialize built-in validators
        self._init_builtin_validators()
        
        # Load schemas if available
        if JSONSCHEMA_AVAILABLE:
            self._load_schemas()
    
    def _init_builtin_validators(self):
        """Initialize built-in custom validators."""
        self.custom_validators.update({
            "port": self._validate_port,
            "ip_address": self._validate_ip_address,
            "url": self._validate_url,
            "path": self._validate_path,
            "agent_name": self._validate_agent_name,
            "environment": self._validate_environment,
            "log_level": self._validate_log_level,
            "timeout": self._validate_timeout,
            "redis_url": self._validate_redis_url,
            "zmq_endpoint": self._validate_zmq_endpoint
        })
    
    def _load_schemas(self):
        """Load JSON schemas from schema directory."""
        if not self.schema_dir.exists():
            self.schema_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_schemas()
        
        for schema_file in self.schema_dir.glob("*.json"):
            try:
                with open(schema_file, 'r') as f:
                    schema = json.load(f)
                    schema_name = schema_file.stem
                    self.schema_cache[schema_name] = schema
                    self.logger.debug(f"Loaded schema: {schema_name}")
            except Exception as e:
                self.logger.warning(f"Failed to load schema {schema_file}: {e}")
    
    def _create_default_schemas(self):
        """Create default validation schemas."""
        # Base configuration schema
        base_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "AI System Base Configuration",
            "type": "object",
            "properties": {
                "system": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "minLength": 1},
                        "version": {"type": "string", "pattern": r"^\d+\.\d+\.\d+$"},
                        "environment": {"type": "string", "enum": ["dev", "staging", "prod"]},
                        "debug": {"type": "boolean"}
                    },
                    "required": ["name", "environment"]
                },
                "logging": {
                    "type": "object", 
                    "properties": {
                        "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                        "file": {"type": "string"},
                        "max_bytes": {"type": "integer", "minimum": 1024},
                        "backup_count": {"type": "integer", "minimum": 1}
                    },
                    "required": ["level"]
                },
                "network": {
                    "type": "object",
                    "properties": {
                        "host": {"type": "string"},
                        "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                        "timeout": {"type": "number", "minimum": 0.1}
                    }
                },
                "performance": {
                    "type": "object",
                    "properties": {
                        "max_workers": {"type": "integer", "minimum": 1},
                        "batch_size": {"type": "integer", "minimum": 1},
                        "cache_size": {"type": "integer", "minimum": 0}
                    }
                }
            },
            "required": ["system", "logging"]
        }
        
        # Agent-specific schema
        agent_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "AI System Agent Configuration",
            "allOf": [{"$ref": "base.json"}],
            "properties": {
                "agent": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "pattern": r"^[a-z_][a-z0-9_]*$"},
                        "type": {"type": "string"},
                        "enabled": {"type": "boolean"},
                        "health_check": {
                            "type": "object",
                            "properties": {
                                "enabled": {"type": "boolean"},
                                "interval": {"type": "integer", "minimum": 1},
                                "timeout": {"type": "number", "minimum": 0.1}
                            }
                        }
                    },
                    "required": ["name", "type"]
                }
            },
            "required": ["agent"]
        }
        
        # Save schemas
        with open(self.schema_dir / "base.json", 'w') as f:
            json.dump(base_schema, f, indent=2)
        
        with open(self.schema_dir / "agent.json", 'w') as f:
            json.dump(agent_schema, f, indent=2)
    
    def validate_config(self, config_data: Dict[str, Any], schema_name: str = "base") -> ValidationResult:
        """Validate configuration against schema and custom rules."""
        errors = []
        warnings = []
        schema_errors = []
        custom_errors = []
        
        # JSON Schema validation
        if JSONSCHEMA_AVAILABLE and schema_name in self.schema_cache:
            try:
                schema = self.schema_cache[schema_name]
                validate(instance=config_data, schema=schema)
                self.logger.debug(f"Schema validation passed: {schema_name}")
            except ValidationError as e:
                schema_errors.append(f"Schema validation failed: {e.message}")
                if self.level == ValidationLevel.STRICT:
                    errors.extend(schema_errors)
                else:
                    warnings.extend(schema_errors)
        
        # Custom validation
        custom_results = self._run_custom_validations(config_data)
        custom_errors.extend(custom_results)
        
        if self.level == ValidationLevel.STRICT:
            errors.extend(custom_errors)
        else:
            warnings.extend(custom_errors)
        
        # Environment-specific validation
        env_results = self._validate_environment_specific(config_data)
        if self.level != ValidationLevel.LENIENT:
            warnings.extend(env_results)
        
        valid = len(errors) == 0
        return ValidationResult(
            valid=valid,
            errors=errors,
            warnings=warnings,
            schema_errors=schema_errors,
            custom_errors=custom_errors
        )
    
    def _run_custom_validations(self, config_data: Dict[str, Any]) -> List[str]:
        """Run custom validation rules."""
        errors = []
        
        # Validate specific fields using custom validators
        validations = [
            ("network.port", "port"),
            ("network.host", "ip_address"),
            ("network.timeout", "timeout"),
            ("logging.level", "log_level"),
            ("system.environment", "environment"),
            ("agent.name", "agent_name") if "agent" in config_data else None
        ]
        
        for validation in validations:
            if validation is None:
                continue
                
            field_path, validator_name = validation
            value = self._get_nested_value(config_data, field_path)
            
            if value is not None and validator_name in self.custom_validators:
                validator = self.custom_validators[validator_name]
                try:
                    if not validator(value):
                        errors.append(f"Invalid {field_path}: {value}")
                except Exception as e:
                    errors.append(f"Validation error for {field_path}: {e}")
        
        return errors
    
    def _validate_environment_specific(self, config_data: Dict[str, Any]) -> List[str]:
        """Validate environment-specific requirements."""
        warnings = []
        
        env = config_data.get("system", {}).get("environment", "dev")
        
        if env == "prod":
            # Production-specific validations
            if config_data.get("system", {}).get("debug", False):
                warnings.append("Debug mode should be disabled in production")
            
            log_level = config_data.get("logging", {}).get("level", "INFO")
            if log_level == "DEBUG":
                warnings.append("DEBUG logging not recommended in production")
            
            # Check security settings
            if not config_data.get("security", {}).get("enable_auth", True):
                warnings.append("Authentication should be enabled in production")
        
        elif env == "dev":
            # Development-specific validations
            if not config_data.get("system", {}).get("debug", True):
                warnings.append("Debug mode recommended in development")
        
        return warnings
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = path.split(".")
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    # Custom validators
    def _validate_port(self, value: Any) -> bool:
        """Validate port number."""
        try:
            port = int(value)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False
    
    def _validate_ip_address(self, value: Any) -> bool:
        """Validate IP address."""
        if not isinstance(value, str):
            return False
        
        # Special cases
        if value in ["localhost", "0.0.0.0", "*"]:
            return True
        
        try:
            socket.inet_aton(value)
            return True
        except socket.error:
            return False
    
    def _validate_url(self, value: Any) -> bool:
        """Validate URL format."""
        if not isinstance(value, str):
            return False
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        return url_pattern.match(value) is not None
    
    def _validate_path(self, value: Any) -> bool:
        """Validate file path."""
        if not isinstance(value, str):
            return False
        
        try:
            path = Path(value)
            # Check if parent directory exists or can be created
            return path.parent.exists() or len(str(path)) > 0
        except Exception:
            return False
    
    def _validate_agent_name(self, value: Any) -> bool:
        """Validate agent name format."""
        if not isinstance(value, str):
            return False
        
        # Agent names should be lowercase with underscores
        pattern = re.compile(r'^[a-z_][a-z0-9_]*$')
        return pattern.match(value) is not None
    
    def _validate_environment(self, value: Any) -> bool:
        """Validate environment name."""
        return value in ["dev", "staging", "prod"]
    
    def _validate_log_level(self, value: Any) -> bool:
        """Validate logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        return value in valid_levels
    
    def _validate_timeout(self, value: Any) -> bool:
        """Validate timeout value."""
        try:
            timeout = float(value)
            return timeout > 0
        except (ValueError, TypeError):
            return False
    
    def _validate_redis_url(self, value: Any) -> bool:
        """Validate Redis URL format."""
        if not isinstance(value, str):
            return False
        
        redis_pattern = re.compile(r'^redis://(?:[\w:]+@)?[\w.-]+(?::\d+)?(?:/\d+)?$')
        return redis_pattern.match(value) is not None
    
    def _validate_zmq_endpoint(self, value: Any) -> bool:
        """Validate ZMQ endpoint format."""
        if not isinstance(value, str):
            return False
        
        # Common ZMQ transports
        zmq_pattern = re.compile(r'^(tcp|ipc|inproc|pgm|epgm)://[\w.-]+(?::\d+)?$')
        return zmq_pattern.match(value) is not None
    
    def add_custom_validator(self, name: str, validator: Callable[[Any], bool]):
        """Add custom validator function."""
        self.custom_validators[name] = validator
        self.logger.debug(f"Added custom validator: {name}")


# Convenience functions for integration with unified config manager
def validate_config_file(config_path: Path, schema_name: str = "base", 
                        level: ValidationLevel = ValidationLevel.MODERATE) -> ValidationResult:
    """Validate configuration file."""
    try:
        with open(config_path, 'r') as f:
            import yaml
            config_data = yaml.safe_load(f)
        
        validator = ConfigValidator(level=level)
        return validator.validate_config(config_data, schema_name)
        
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[f"Failed to load config file: {e}"],
            warnings=[]
        )


def validate_agent_config(agent_file: Path, level: ValidationLevel = ValidationLevel.MODERATE) -> ValidationResult:
    """Validate agent configuration using Config.for_agent()."""
    try:
        # Use the unified config manager
        config = Config.for_agent(str(agent_file))
        config_data = config._config_data  # Access internal data
        
        validator = ConfigValidator(level=level)
        return validator.validate_config(config_data, "agent")
        
    except Exception as e:
        return ValidationResult(
            valid=False,
            errors=[f"Failed to validate agent config: {e}"],
            warnings=[]
        )


# CLI integration for validation
def validate_all_configs(config_dir: Path = None, schema_name: str = "base") -> Dict[str, ValidationResult]:
    """Validate all configuration files in a directory."""
    if config_dir is None:
        config_dir = Path(__file__).parent / "defaults"
    
    results = {}
    validator = ConfigValidator()
    
    for config_file in config_dir.glob("*.yaml"):
        try:
            with open(config_file, 'r') as f:
                import yaml
                config_data = yaml.safe_load(f)
            
            result = validator.validate_config(config_data, schema_name)
            results[config_file.name] = result
            
        except Exception as e:
            results[config_file.name] = ValidationResult(
                valid=False,
                errors=[f"Failed to process file: {e}"],
                warnings=[]
            )
    
    return results


# Enhanced error reporting
class ValidationReporter:
    """Enhanced validation error reporting."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("config.validation.reporter")
    
    def report_validation_result(self, result: ValidationResult, config_name: str = "config"):
        """Report validation results with appropriate logging levels."""
        if result.valid:
            self.logger.info(f"✅ {config_name} validation passed")
        else:
            self.logger.error(f"❌ {config_name} validation failed")
        
        # Report errors
        for error in result.errors:
            self.logger.error(f"  ERROR: {error}")
        
        # Report warnings
        for warning in result.warnings:
            self.logger.warning(f"  WARNING: {warning}")
        
        # Report schema errors separately
        if result.schema_errors:
            for error in result.schema_errors:
                self.logger.error(f"  SCHEMA: {error}")
        
        # Report custom errors separately
        if result.custom_errors:
            for error in result.custom_errors:
                self.logger.error(f"  CUSTOM: {error}")
    
    def generate_report(self, results: Dict[str, ValidationResult]) -> str:
        """Generate comprehensive validation report."""
        report_lines = ["Configuration Validation Report", "=" * 40, ""]
        
        total_configs = len(results)
        valid_configs = sum(1 for r in results.values() if r.valid)
        
        report_lines.append(f"Total configurations: {total_configs}")
        report_lines.append(f"Valid configurations: {valid_configs}")
        report_lines.append(f"Invalid configurations: {total_configs - valid_configs}")
        report_lines.append("")
        
        for config_name, result in results.items():
            status = "✅ VALID" if result.valid else "❌ INVALID"
            report_lines.append(f"{config_name}: {status}")
            
            if result.errors:
                report_lines.append("  Errors:")
                for error in result.errors:
                    report_lines.append(f"    - {error}")
            
            if result.warnings:
                report_lines.append("  Warnings:")
                for warning in result.warnings:
                    report_lines.append(f"    - {warning}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)


# Global validation instance for easy access
_global_validator = None

def get_validator(level: ValidationLevel = ValidationLevel.MODERATE) -> ConfigValidator:
    """Get global configuration validator."""
    global _global_validator
    
    if _global_validator is None:
        _global_validator = ConfigValidator(level=level)
    
    return _global_validator
