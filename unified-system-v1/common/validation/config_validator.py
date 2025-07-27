"""
Configuration validator for AI Agent startup configs.

Validates agent configuration YAML files against JSON schema to prevent
config drift and ensure consistency between MainPC and PC2 systems.
"""

import yaml
import jsonschema
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ConfigValidator:
    """JSON Schema validator for agent startup configurations."""
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize validator with schema file."""
        if schema_path is None:
            # Default schema location
            schema_path = Path(__file__).parent / "schemas" / "agent_config.schema.yaml"
        
        self.schema_path = schema_path
        self.schema = self._load_schema()
    
    def _load_schema(self) -> Dict:
        """Load JSON schema from YAML file."""
        try:
            with open(self.schema_path, 'r') as f:
                schema = yaml.safe_load(f)
            logger.info(f"Schema loaded from {self.schema_path}")
            return schema
        except FileNotFoundError:
            logger.error(f"Schema file not found: {self.schema_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in schema file: {e}")
            raise
    
    def validate_config(self, config_path: Path, warn_mode: bool = False) -> Tuple[bool, List[str]]:
        """
        Validate configuration file against schema.
        
        Args:
            config_path: Path to YAML config file
            warn_mode: If True, return warnings instead of failing
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        try:
            # Load config file
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Validate against schema
            jsonschema.validate(instance=config, schema=self.schema)
            
            logger.info(f"✅ Configuration valid: {config_path}")
            return True, []
            
        except FileNotFoundError:
            error = f"❌ Config file not found: {config_path}"
            logger.error(error)
            return False, [error]
            
        except yaml.YAMLError as e:
            error = f"❌ Invalid YAML in config: {e}"
            logger.error(error)
            return False, [error]
            
        except jsonschema.ValidationError as e:
            error = f"❌ Schema validation error: {e.message}"
            if warn_mode:
                logger.warning(f"⚠️  {error}")
                return True, [error]  # Pass but with warnings
            else:
                logger.error(error)
                return False, [error]
        
        except jsonschema.SchemaError as e:
            error = f"❌ Schema definition error: {e.message}"
            logger.error(error)
            return False, [error]
    
    def validate_multiple_configs(self, config_paths: List[Path], warn_mode: bool = False) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate multiple configuration files.
        
        Args:
            config_paths: List of paths to YAML config files
            warn_mode: If True, return warnings instead of failing
            
        Returns:
            Dict mapping config path to (is_valid, list_of_errors)
        """
        results = {}
        
        for config_path in config_paths:
            is_valid, errors = self.validate_config(config_path, warn_mode)
            results[str(config_path)] = (is_valid, errors)
        
        return results
    
    def print_validation_report(self, results: Dict[str, Tuple[bool, List[str]]]) -> None:
        """Print formatted validation report."""
        total_configs = len(results)
        valid_configs = sum(1 for is_valid, _ in results.values() if is_valid)
        
        print(f"\n🔍 CONFIGURATION VALIDATION REPORT")
        print(f"=" * 50)
        print(f"Total configs checked: {total_configs}")
        print(f"Valid configs: {valid_configs}")
        print(f"Invalid configs: {total_configs - valid_configs}")
        print()
        
        for config_path, (is_valid, errors) in results.items():
            status = "✅ VALID" if is_valid else "❌ INVALID"
            print(f"{status}: {config_path}")
            
            if errors:
                for error in errors:
                    print(f"  - {error}")
            print() 