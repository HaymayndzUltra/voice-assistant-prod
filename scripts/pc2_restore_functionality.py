#!/usr/bin/env python3
"""
PC2 Functionality Restoration Script
-----------------------------------
Restores functionality to PC2 agents after fixing architectural compliance.

This script:
1. Creates backups of original PC2 agents before fixing compliance
2. Applies compliance fixes
3. Restores any functionality lost during compliance fixing
4. Ensures both compliance standards and original functionality are preserved
"""

import os
import re
import sys
import shutil
import difflib
import ast
import yaml
from pathlib import Path
import logging
from typing import Dict, List, Set, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pc2_restore_functionality")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PC2_CODE = PROJECT_ROOT / 'pc2_code'
PC2_CONFIG_PATH = PC2_CODE / 'config' / 'startup_config.yaml'
PC2_AGENTS_DIR = PC2_CODE / 'agents'
PC2_BACKUPS_DIR = PC2_AGENTS_DIR / 'backups'

def create_backup(file_path: Path) -> Path:
    """Create a backup of a file before modifying it."""
    # Make sure backup directory exists
    PC2_BACKUPS_DIR.mkdir(exist_ok=True)
    
    # Create a backup in the backups directory with original filename
    backup_path = PC2_BACKUPS_DIR / file_path.name
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
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
                if len([m for m in node.body if isinstance(m, ast.FunctionDef)]) > 1:
                    return node.name
    except Exception as e:
        logger.error(f"Error extracting class name: {e}")
    return None

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

def gather_agents_from_config() -> List[Dict]:
    """Gather agents from PC2 startup_config.yaml."""
    try:
        with open(PC2_CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        agents = []
        # Process all sections in the config file
        for section_name, section_data in config.items():
            if isinstance(section_data, list):
                for agent in section_data:
                    if isinstance(agent, dict) and 'script_path' in agent:
                        agent_name = agent.get('name', os.path.basename(agent['script_path']).split('.')[0])
                        agents.append({
                            'name': agent_name,
                            'script_path': agent['script_path']
                        })
        
        return agents
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return []

def restore_agent_functionality(agent: Dict) -> bool:
    """Restore functionality for a specific agent."""
    rel_path = agent['script_path']
    agent_name = agent['name']
    abs_path = (PC2_CODE / rel_path).resolve()
    
    # Path to the backup file
    backup_path = PC2_BACKUPS_DIR / os.path.basename(abs_path)
    
    if not abs_path.exists():
        logger.error(f"Agent not found: {abs_path}")
        return False
    
    if not backup_path.exists():
        logger.warning(f"No backup found for {agent_name}, creating one now")
        backup_path = create_backup(abs_path)
    
    logger.info(f"Restoring functionality for {agent_name}")
    
    # Read both files
    try:
        with open(abs_path, 'r', encoding='utf-8') as f:
            refactored_code = f.read()
        
        with open(backup_path, 'r', encoding='utf-8') as f:
            original_code = f.read()
        
        # Extract methods from both files
        refactored_methods = extract_methods(refactored_code)
        original_methods = extract_methods(original_code)
        
        # Extract class names
        refactored_class = extract_class_name(refactored_code)
        original_class = extract_class_name(original_code)
        
        if not refactored_class or not original_class:
            logger.error(f"Could not extract class names for {agent_name}")
            return False
        
        logger.info(f"Found classes: {original_class} (original) -> {refactored_class} (refactored)")
        
        # Find methods in original that are missing in refactored
        missing_methods = set(original_methods.keys()) - set(refactored_methods.keys())
        
        # Exclude methods that should not be directly copied
        excluded_methods = {'__init__', '__enter__', '__exit__', '_get_health_status', 'cleanup'}
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
        
        # Write the new code
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(new_code)
        
        logger.info(f"Successfully restored functionality for {agent_name}")
        return True
    
    except Exception as e:
        logger.error(f"Error restoring functionality for {agent_name}: {e}")
        return False

def restore_all_agents():
    """Restore functionality for all agents in PC2 config."""
    agents = gather_agents_from_config()
    if not agents:
        logger.error("No agents found in config")
        return 0
    
    logger.info(f"Found {len(agents)} agents in PC2 config")
    
    success_count = 0
    for agent in agents:
        if restore_agent_functionality(agent):
            success_count += 1
    
    logger.info(f"Successfully restored functionality for {success_count}/{len(agents)} agents")
    return success_count

def main():
    """Main function."""
    # Create backup directory if it doesn't exist
    PC2_BACKUPS_DIR.mkdir(exist_ok=True)
    
    # Restore functionality for all agents
    restored_count = restore_all_agents()
    
    # Run compliance check to verify
    print("\nRunning compliance check...")
    os.system(f"python3 {PROJECT_ROOT}/scripts/enhanced_system_audit.py")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 