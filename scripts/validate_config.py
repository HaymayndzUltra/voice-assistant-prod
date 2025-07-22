#!/usr/bin/env python3
"""
Configuration validator script for AI Agent startup configs.

This script validates agent configuration YAML files against JSON schema
to prevent config drift and ensure consistency between MainPC and PC2 systems.

Usage:
    python scripts/validate_config.py main_pc_code/config/startup_config.yaml
    python scripts/validate_config.py pc2_code/config/startup_config.yaml --warn
    python scripts/validate_config.py --all --strict
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import List

# Add common to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.validation.config_validator import ConfigValidator


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def find_config_files() -> List[Path]:
    """Find all startup config files in the repository."""
    project_root = Path(__file__).parent.parent
    config_files = []
    
    # MainPC config
    mainpc_config = project_root / "main_pc_code" / "config" / "startup_config.yaml"
    if mainpc_config.exists():
        config_files.append(mainpc_config)
    
    # PC2 config
    pc2_config = project_root / "pc2_code" / "config" / "startup_config.yaml"
    if pc2_config.exists():
        config_files.append(pc2_config)
    
    return config_files


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate AI agent startup configuration files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s main_pc_code/config/startup_config.yaml
  %(prog)s pc2_code/config/startup_config.yaml --warn
  %(prog)s --all --strict
  %(prog)s --all --warn --verbose
        """
    )
    
    parser.add_argument(
        'config_file',
        nargs='?',
        type=Path,
        help='Path to configuration file to validate'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Validate all known configuration files'
    )
    
    parser.add_argument(
        '--warn',
        action='store_true',
        help='Show warnings instead of failing on validation errors'
    )
    
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Strict mode - fail on any validation errors (default)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--schema',
        type=Path,
        help='Path to custom schema file (optional)'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Determine warn mode
    warn_mode = args.warn and not args.strict
    
    try:
        # Initialize validator
        validator = ConfigValidator(args.schema)
        logger.info("✅ Schema loaded successfully")
        
        # Determine which files to validate
        if args.all:
            config_files = find_config_files()
            if not config_files:
                logger.error("❌ No configuration files found")
                sys.exit(1)
            logger.info(f"Found {len(config_files)} configuration files")
        elif args.config_file:
            if not args.config_file.exists():
                logger.error(f"❌ Configuration file not found: {args.config_file}")
                sys.exit(1)
            config_files = [args.config_file]
        else:
            logger.error("❌ Must specify either a config file or --all")
            parser.print_help()
            sys.exit(1)
        
        # Validate configurations
        logger.info(f"Validating {len(config_files)} configuration file(s)...")
        results = validator.validate_multiple_configs(config_files, warn_mode)
        
        # Print results
        validator.print_validation_report(results)
        
        # Determine exit code
        all_valid = all(is_valid for is_valid, _ in results.values())
        
        if all_valid:
            logger.info("🎉 All configurations are valid!")
            sys.exit(0)
        else:
            if warn_mode:
                logger.warning("⚠️  Some configurations have warnings")
                sys.exit(0)  # Don't fail in warn mode
            else:
                logger.error("❌ Some configurations are invalid")
                sys.exit(1)
    
    except Exception as e:
        logger.error(f"❌ Validation failed with error: {e}")
        if args.verbose:
            logger.exception("Full exception details:")
        sys.exit(1)


if __name__ == "__main__":
    main() 