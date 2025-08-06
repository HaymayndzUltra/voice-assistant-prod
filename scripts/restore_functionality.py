#!/usr/bin/env python3
"""
Functionality Restoration Script
-------------------------------
Restores functionality from PC2 agents to MainPC agents while maintaining architectural compliance.

This script:
1. Compares original PC2 agents with refactored MainPC agents
2. Identifies missing functionality
3. Restores functionality while maintaining architectural compliance
4. Replaces config_parser with config_loader
"""

import os
import re
import sys
import shutil
import difflib
import ast
from pathlib import Path
import logging
from typing import Dict, List, Set, Tuple, Optional
from common.utils.log_setup import configure_logging

# Configure logging
logger = configure_logging(__name__)
logger = logging.getLogger("restore_functionality")

# Define paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAIN_PC_CODE = PROJECT_ROOT / 'main_pc_code'
PC2_BACKUP = MAIN_PC_CODE / 'MAINPCRESTOREFROMPC2'
AGENTS_DIR = MAIN_PC_CODE / 'agents'
SRC_AGENTS_DIR = MAIN_PC_CODE / 'src'
PC2_AGENTS_DIR = PC2_BACKUP / 'agents'
PC2_SRC_DIR = PC2_BACKUP / 'src'
PC2_FORMAINPC_DIR = PC2_BACKUP / 'FORMAINPC'
FORMAINPC_DIR = MAIN_PC_CODE / 'FORMAINPC'

# Dictionary of agents to restore functionality with their paths
AGENTS_TO_RESTORE = {
    "fused_audio_preprocessor.py": {
        "main_path": MAIN_PC_CODE / 'src' / 'audio' / 'fused_audio_preprocessor.py', 
        "backup_path": PC2_BACKUP / 'src' / 'audio' / 'fused_audio_preprocessor.py'
    },
    "wake_word_detector.py": {
        "main_path": MAIN_PC_CODE / 'agents' / 'wake_word_detector.py',
        "backup_path": PC2_BACKUP / 'agents' / 'wake_word_detector.py'
    },
    "vision_capture_agent.py": {
        "main_path": MAIN_PC_CODE / 'src' / 'vision' / 'vision_capture_agent.py',
        "backup_path": PC2_BACKUP / 'src' / 'vision' / 'vision_capture_agent.py'
    },
    "face_recognition_agent.py": {
        "main_path": MAIN_PC_CODE / 'agents' / 'face_recognition_agent.py',
        "backup_path": PC2_BACKUP / 'agents' / 'face_recognition_agent.py'
    },
    "SelfTrainingOrchestrator.py": {
        "main_path": MAIN_PC_CODE / 'FORMAINPC' / 'SelfTrainingOrchestrator.py',
        "backup_path": PC2_BACKUP / 'FORMAINPC' / 'SelfTrainingOrchestrator.py'
    }
}

def create_backup(file_path: Path) -> Path:
    """Create a backup of a file before modifying it."""
    backup_path = file_path.with_suffix(file_path.suffix + '.bak')
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
                if len([m for m in node.body if isinstance(m, ast.FunctionDef)]) > 3:
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

def restore_agent_functionality(agent_name: str, paths: dict) -> bool:
    """Restore functionality for a specific agent."""
    refactored_path = paths["main_path"]
    original_path = paths["backup_path"]
    
    if not refactored_path.exists():
        logger.error(f"Refactored agent not found: {refactored_path}")
        return False
    
    if not original_path.exists():
        logger.error(f"Original agent not found: {original_path}")
        return False
    
    logger.info(f"Restoring functionality for {agent_name}")
    
    # Create backup of refactored agent
    backup_path = create_backup(refactored_path)
    
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
    
    if not refactored_class or not original_class:
        logger.error(f"Could not extract class names for {agent_name}")
        return False
    
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
    
    logger.info(f"Successfully restored functionality for {agent_name}")
    return True

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

def main():
    """Main function to restore functionality for all specified agents."""
    # Check if PC2 backup directory exists
    if not PC2_BACKUP.exists():
        logger.error(f"PC2 backup directory not found: {PC2_BACKUP}")
        return 1
    
    # Create backup directory if it doesn't exist
    backup_dir = AGENTS_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    # Only restore SelfTrainingOrchestrator
    agent_name = "SelfTrainingOrchestrator.py"
    if agent_name in AGENTS_TO_RESTORE:
        success = restore_agent_functionality(agent_name, AGENTS_TO_RESTORE[agent_name])
        logger.info(f"{'Successfully restored' if success else 'Failed to restore'} functionality for {agent_name}")
        return 0 if success else 1
    else:
        logger.error(f"Agent {agent_name} not found in AGENTS_TO_RESTORE")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 