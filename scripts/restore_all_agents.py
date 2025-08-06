#!/usr/bin/env python3
"""
Full System Functionality Restoration Script
-------------------------------------------
Restores functionality for all agents in the system from PC2 backups while maintaining architectural compliance.

This script:
1. Loads all agents from startup_config.yaml
2. Compares each with its PC2 backup (if available)
3. Restores missing functionality while maintaining architectural compliance
4. Replaces config_parser with config_loader
5. Creates backups before making any changes
"""

import os
import re
import sys
import shutil
import ast
import yaml
from pathlib import Path
import logging
from typing import Dict, List, Set, Tuple, Optional
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('restore_all_agents.log')
    ]
)
logger = logging.getLogger("restore_all_agents")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_BACKUP = MAIN_PC_CODE / 'MAINPCRESTOREFROMPC2'
CONFIG_PATH = MAIN_PC_CODE / 'config' / 'startup_config.yaml'
BACKUP_DIR = MAIN_PC_CODE / 'agent_backups'

def create_backup(file_path: Path) -> Path:
    """Create a backup of a file before modifying it."""
    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Create a backup with timestamp in the backup directory
    backup_filename = f"{file_path.stem}_{file_path.suffix.replace('.', '')}_{os.path.getmtime(file_path):.0f}.bak"
    backup_path = BACKUP_DIR / backup_filename
    
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    # Also create a direct .bak file next to the original for easy recovery
    direct_backup = file_path.with_suffix(file_path.suffix + '.bak')
    if not direct_backup.exists():
        shutil.copy2(file_path, direct_backup)
    
    return backup_path

def extract_methods(source_code: str) -> Dict[str, str]:
    """Extract method names and their content from source code."""
    methods = {}
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for method in node.body:
                    if isinstance(method, ast.FunctionDef):
                        method_source = ast.get_source_segment(source_code, method)
                        if method_source:
                            methods[method.name] = method_source
    except Exception as e:
        logger.error(f"Error parsing source code: {e}")
    return methods

def extract_class_name(source_code: str) -> Optional[str]:
    """Extract the main class name from source code."""
    try:
        tree = ast.parse(source_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Find the class with the most methods (likely the main agent class)
                if len([m for m in node.body if isinstance(m, ast.FunctionDef)]) > 3:
                    return node.name
        
        # If no class with more than 3 methods found, return the first class
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                return node.name
                
    except Exception as e:
        logger.error(f"Error extracting class name: {e}")
    return None

def replace_config_parser_with_loader(content: str) -> str:
    """Replace config_parser with config_loader in the source code."""
    # Replace imports
    content = re.sub(
        r'from\s+(?:main_pc_code\.)?utils\.config_parser\s+import\s+parse_agent_args',
        'from main_pc_code.utils.config_loader import load_config',
        content
    )
    
    # Replace usage
    content = re.sub(
        r'_agent_args\s*=\s*parse_agent_args\(\)',
        'config = load_config()',
        content
    )
    
    # Replace references to _agent_args
    content = re.sub(
        r'_agent_args\.(\w+)',
        r'config.get("\1")',
        content
    )
    
    content = re.sub(
        r'getattr\(_agent_args,\s*[\'"](\w+)[\'"],\s*([^)]+)\)',
        r'config.get("\1", \2)',
        content
    )
    
    return content

def extract_init_content(init_method: str) -> str:
    """Extract the content of the __init__ method excluding the signature and super call."""
    if not init_method:
        return ""
    
    # Split the method into lines
    lines = init_method.split('\n')
    
    # Remove the method signature (first line)
    content_lines = lines[1:] if lines else []
    
    # Remove any super().__init__ calls
    filtered_lines = []
    for line in content_lines:
        if not re.search(r'super\(\)\.__init__', line):
            filtered_lines.append(line)
    
    # Find the common indentation
    common_indent = None
    for line in filtered_lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if common_indent is None or indent < common_indent:
                common_indent = indent
    
    # Remove the common indentation
    if common_indent:
        filtered_lines = [line[common_indent:] if line.strip() else line for line in filtered_lines]
    
    return '\n'.join(filtered_lines)

def restore_agent_functionality(agent_path: str) -> bool:
    """Restore functionality for a specific agent."""
    # Extract the base filename
    agent_filename = os.path.basename(agent_path)
    
    # Handle special paths like FORMAINPC/ or src/
    if agent_path.startswith('FORMAINPC/'):
        refactored_path = MAIN_PC_CODE / agent_path
        original_path = PC2_BACKUP / 'FORMAINPC' / agent_filename
    elif agent_path.startswith('src/'):
        refactored_path = MAIN_PC_CODE / agent_path
        original_path = PC2_BACKUP / 'src' / agent_filename
    else:
        refactored_path = MAIN_PC_CODE / agent_path
        original_path = PC2_BACKUP / 'agents' / agent_filename
    
    if not refactored_path.exists():
        logger.error(f"Refactored agent not found: {refactored_path}")
        return False
    
    if not original_path.exists():
        logger.warning(f"Original agent not found: {original_path}. Skipping restoration but will replace config_parser.")
        # Even if we don't have the original, we can still replace config_parser
        try:
            with open(refactored_path, 'r', encoding='utf-8') as f:
                refactored_code = f.read()
            
            # Replace config_parser with config_loader
            new_code = replace_config_parser_with_loader(refactored_code)
            
            # Only write if changes were made
            if new_code != refactored_code:
                # Create backup
                create_backup(refactored_path)
                
                # Write the updated code
                with open(refactored_path, 'w', encoding='utf-8') as f:
                    f.write(new_code)
                logger.info(f"Replaced config_parser with config_loader in {agent_filename}")
            
            return True
        except Exception as e:
            logger.error(f"Error replacing config_parser in {agent_filename}: {e}")
            return False
    
    logger.info(f"Restoring functionality for {agent_filename}")
    
    # Create backup of refactored agent
    backup_path = create_backup(refactored_path)
    
    try:
        # Read both files
        with open(refactored_path, 'r', encoding='utf-8') as f:
            refactored_code = f.read()
        
        with open(original_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        # Extract methods from both files
        refactored_methods = extract_methods(refactored_code)
        original_methods = extract_methods(original_code)
        
        # Extract class names
        refactored_class = extract_class_name(refactored_code)
        original_class = extract_class_name(original_code)
        
        if not refactored_class:
            logger.warning(f"Could not extract refactored class name for {agent_filename}. Will only replace config_parser.")
            # Replace config_parser with config_loader
            new_code = replace_config_parser_with_loader(refactored_code)
            
            # Write the updated code
            with open(refactored_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            logger.info(f"Replaced config_parser with config_loader in {agent_filename}")
            return True
        
        if not original_class:
            logger.warning(f"Could not extract original class name for {agent_filename}. Will only replace config_parser.")
            # Replace config_parser with config_loader
            new_code = replace_config_parser_with_loader(refactored_code)
            
            # Write the updated code
            with open(refactored_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            logger.info(f"Replaced config_parser with config_loader in {agent_filename}")
            return True
        
        logger.info(f"Found classes: {original_class} (original) -> {refactored_class} (refactored)")
        
        # Find methods in original that are missing in refactored
        missing_methods = set(original_methods.keys()) - set(refactored_methods.keys())
        
        # Exclude __init__ and other methods that should not be directly copied
        excluded_methods = {'__init__', '__enter__', '__exit__', 'run', '_get_health_status', 'cleanup'}
        missing_methods = missing_methods - excluded_methods
        
        logger.info(f"Found {len(missing_methods)} missing methods to restore")
        
        # Extract the original __init__ content to merge with refactored __init__
        original_init = original_methods.get('__init__', '')
        init_content = extract_init_content(original_init)
        
        # Prepare the new code
        new_code = refactored_code
        
        # Replace class name in original methods to match refactored class name
        if original_class != refactored_class:
            pattern = re.compile(r'\b' + re.escape(original_class) + r'\b')
        
        # Add missing methods from original to refactored
        for method_name in sorted(missing_methods):
            method_code = original_methods[method_name]
            
            # Replace class name if different
            if original_class != refactored_class:
                method_code = pattern.sub(refactored_class, method_code)
            
            # Find where to insert the method
            # Look for the last method in the class
            last_method_match = re.search(r'(\s+)def\s+\w+\s*\([^)]*\):\s*(?:"""[\s\S]*?""")?\s*(?:#[^\n]*)?\s*(?:pass)?(?=\n\1\S|\n\n|\Z)', new_code)
            
            if last_method_match:
                insert_pos = last_method_match.end()
                indentation = last_method_match.group(1)
                
                # Ensure proper indentation of the method
                method_lines = method_code.split('\n')
                if method_lines and method_lines[0].startswith('def '):
                    # Remove 'def ' from the first line and add indentation
                    method_lines[0] = indentation + method_lines[0]
                    # Indent the rest of the lines
                    for i in range(1, len(method_lines)):
                        if method_lines[i].strip():
                            method_lines[i] = indentation + method_lines[i]
                    
                    method_code = '\n'.join(method_lines)
                
                new_code = new_code[:insert_pos] + '\n\n' + method_code + new_code[insert_pos:]
                logger.info(f"Restored method: {method_name}")
            else:
                logger.warning(f"Could not find position to insert method {method_name}")
        
        # Merge __init__ content
        if init_content:
            # Find the __init__ method in the refactored code
            init_pattern = re.compile(r'(\s+)def\s+__init__\s*\([^)]*\):\s*(?:"""[\s\S]*?""")?\s*(?:#[^\n]*)?\s*super\(\)\.__init__\([^)]*\)')
            init_match = init_pattern.search(new_code)
            
            if init_match:
                # Find the end of super().__init__ line
                super_init_end = init_match.end()
                indentation = init_match.group(1) + '    '  # Add 4 spaces for content indentation
                
                # Format the init content with proper indentation
                formatted_init = '\n'.join(indentation + line for line in init_content.split('\n') if line.strip())
                
                # Insert the init content after super().__init__
                new_code = new_code[:super_init_end] + '\n' + formatted_init + new_code[super_init_end:]
                logger.info("Merged __init__ content")
            else:
                logger.warning("Could not find __init__ method in refactored code")
        
        # Replace config_parser with config_loader
        new_code = replace_config_parser_with_loader(new_code)
        logger.info("Replaced config_parser with config_loader")
        
        # Write the new code
        with open(refactored_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        
        logger.info(f"Successfully restored functionality for {agent_filename}")
        return True
    except Exception as e:
        logger.error(f"Error restoring functionality for {agent_filename}: {e}")
        # Try to restore from backup if we created one
        try:
            if backup_path.exists():
                shutil.copy2(backup_path, refactored_path)
                logger.info(f"Restored {agent_filename} from backup after error")
        except Exception as backup_error:
            logger.error(f"Error restoring from backup: {backup_error}")
        return False

def load_agents_from_config() -> List[str]:
    """Load all agents from the startup_config.yaml file."""
    if not CONFIG_PATH.exists():
        logger.error(f"Config file not found: {CONFIG_PATH}")
        return []
    
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        agents = []
        for section_name, section_data in config.items():
            if isinstance(section_data, list):
                for agent in section_data:
                    if isinstance(agent, dict) and 'script_path' in agent:
                        script_path = agent['script_path']
                        if script_path not in agents:
                            agents.append(script_path)
        
        return agents
    except Exception as e:
        logger.error(f"Error loading agents from config: {e}")
        return []

def main():
    """Main function to restore functionality for all agents."""
    # Check if PC2 backup directory exists
    if not PC2_BACKUP.exists():
        logger.error(f"PC2 backup directory not found: {PC2_BACKUP}")
        return 1
    
    # Create backup directory if it doesn't exist
    BACKUP_DIR.mkdir(exist_ok=True)
    
    # Load agents from config
    agents = load_agents_from_config()
    if not agents:
        logger.error("No agents found in config file")
        return 1
    
    logger.info(f"Found {len(agents)} agents in config file")
    
    # Restore functionality for each agent
    success_count = 0
    for agent_path in agents:
        if restore_agent_functionality(agent_path):
            success_count += 1
    
    logger.info(f"Successfully processed {success_count}/{len(agents)} agents")
    logger.info(f"See restore_all_agents.log for detailed information")
    
    return 0 if success_count > 0 else 1

if __name__ == "__main__":
    sys.exit(main()) 