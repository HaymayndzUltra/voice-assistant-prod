#!/usr/bin/env python3
from common.config_manager import get_service_ip, get_service_url, get_redis_url
from common.utils.log_setup import configure_logging
"""
ZMQ Hardcoded IP Address Refactoring Script

This script updates hardcoded tcp://localhost and tcp://127.0.0.1 IP addresses in Python files
to use the network_utils.get_zmq_connection_string function instead.

Example usages:
- Update a specific file: python update_zmq_hardcoded_ips.py path/to/file.py
- Update multiple files: python update_zmq_hardcoded_ips.py file1.py file2.py
- Update all files in startup_config: python update_zmq_hardcoded_ips.py --from-startup-config
"""

import argparse
import os
import re
import sys
import yaml
import logging
from pathlib import Path
from typing import List, Set
from common.env_helpers import get_env

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger(__name__)

# Regular expressions for finding hardcoded ZMQ connections
IMPORT_PATTERN = re.compile(r'import\s+zmq')
CONNECTION_PATTERN = re.compile(r'(\.connect|\.bind)\(\s*f?["\']tcp://(localhost|127\.0\.0\.1):([^"\']+)["\']')
HARDCODED_ENDPOINT_PATTERN = re.compile(r'(["\']tcp://(localhost|127\.0\.0\.1):([^"\']+)["\']\s*)')
ENDPOINT_VAR_PATTERN = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*f?["\']tcp://(localhost|127\.0\.0\.1):([^"\']*)["\']')

# Network utils import statement
NETWORK_UTILS_IMPORT = "from main_pc_code.utils.network_utils import get_zmq_connection_string, get_machine_ip"

def check_file_needs_update(file_path: Path) -> bool:
    """
    Check if a file contains hardcoded ZMQ connection strings.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        True if file needs updating, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Only check files that use ZMQ
        if not IMPORT_PATTERN.search(content):
            return False
            
        # Check for hardcoded connections
        if (CONNECTION_PATTERN.search(content) or 
            HARDCODED_ENDPOINT_PATTERN.search(content) or
            ENDPOINT_VAR_PATTERN.search(content)):
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error checking {file_path}: {e}")
        return False

def update_file(file_path: Path) -> bool:
    """
    Update a file to use network_utils instead of hardcoded IPs.
    
    Args:
        file_path: Path to the file to update
        
    Returns:
        True if file was updated, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Skip files that don't use ZMQ
        if not IMPORT_PATTERN.search(content):
            logger.debug(f"Skipping {file_path}: No ZMQ import found")
            return False
            
        # Make a copy of the original content
        original_content = content
        
        # Add network_utils import if not already present
        if "from main_pc_code.utils.network_utils import" not in content:
            # Find the last import statement
            import_lines = [line for line in content.split('\n') if 
                          line.strip().startswith('import ') or 
                          line.strip().startswith('from ')]
            
            if import_lines:
                last_import = import_lines[-1]
                content = content.replace(last_import, f"{last_import}\n{NETWORK_UTILS_IMPORT}")
            else:
                # If no imports found, add at the beginning after any comments or docstrings
                lines = content.split('\n')
                insert_pos = 0
                
                # Skip past initial comments and docstrings
                while insert_pos < len(lines):
                    line = lines[insert_pos].strip()
                    if (not line or line.startswith('#') or 
                        (insert_pos == 0 and line.startswith('"""') and not line.endswith('"""'))):
                        insert_pos += 1
                    elif insert_pos > 0 and lines[insert_pos-1].strip().startswith('"""') and line.endswith('"""'):
                        insert_pos += 1
                    else:
                        break
                
                lines.insert(insert_pos, NETWORK_UTILS_IMPORT)
                content = '\n'.join(lines)
        
        # Update connect/bind calls
        content = CONNECTION_PATTERN.sub(
            lambda m: f'{m.group(1)}(get_zmq_connection_string({m.group(3)}, "localhost"))', 
            content
        )
        
        # Update endpoint variables
        content = ENDPOINT_VAR_PATTERN.sub(
            lambda m: f'{m.group(1)} = get_zmq_connection_string({m.group(3)}, "localhost")', 
            content
        )
        
        # Update hardcoded endpoints in other contexts
        content = HARDCODED_ENDPOINT_PATTERN.sub(
            lambda m: f'get_zmq_connection_string({m.group(3)}, "localhost")', 
            content
        )
        
        # Write the updated content if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Updated {file_path}")
            return True
        else:
            logger.debug(f"No changes needed for {file_path}")
            return False
    except Exception as e:
        logger.error(f"Error updating {file_path}: {e}")
        return False

def get_files_from_startup_config() -> Set[Path]:
    """
    Get a list of script paths from the startup_config.yaml file.
    
    Returns:
        Set of Path objects for script files
    """
    script_paths = set()
    config_path = Path("main_pc_code/config/startup_config.yaml")
    
    if not config_path.exists():
        logger.error(f"startup_config.yaml not found at {config_path}")
        return script_paths
        
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        # Extract script paths
        for key, value in config.items():
            if isinstance(value, dict) and 'script_path' in value:
                script_path = Path(value['script_path'])
                if script_path.exists():
                    script_paths.add(script_path)
                    
        logger.info(f"Found {len(script_paths)} script paths in startup_config.yaml")
        return script_paths
    except Exception as e:
        logger.error(f"Error reading startup_config.yaml: {e}")
        return script_paths

def main():
    parser = argparse.ArgumentParser(description='Update hardcoded ZMQ IP addresses')
    parser.add_argument('files', nargs='*', help='Files to update')
    parser.add_argument('--from-startup-config', action='store_true', 
                        help='Update files listed in startup_config.yaml')
    parser.add_argument('--check-only', action='store_true',
                        help='Only check files, don\'t update them')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get the list of files to process
    files_to_process = set()
    
    if args.from_startup_config:
        files_to_process.update(get_files_from_startup_config())
    
    if args.files:
        for file_path in args.files:
            path = Path(file_path)
            if path.exists():
                files_to_process.add(path)
            else:
                logger.warning(f"File not found: {file_path}")
    
    if not files_to_process:
        logger.error("No files to process")
        sys.exit(1)
    
    # Process files
    files_needing_update = []
    files_updated = []
    
    for file_path in sorted(files_to_process):
        if not str(file_path).endswith('.py'):
            logger.debug(f"Skipping non-Python file: {file_path}")
            continue
            
        if check_file_needs_update(file_path):
            files_needing_update.append(file_path)
            if not args.check_only and update_file(file_path):
                files_updated.append(file_path)
    
    # Report results
    logger.info(f"Files checked: {len(files_to_process)}")
    logger.info(f"Files needing update: {len(files_needing_update)}")
    
    if args.check_only:
        for file_path in files_needing_update:
            print(f"Needs update: {file_path}")
    else:
        logger.info(f"Files updated: {len(files_updated)}")
        for file_path in files_updated:
            print(f"Updated: {file_path}")

if __name__ == '__main__':
    main() 