#!/usr/bin/env python3
import os
import sys
import py_compile
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def find_agent_files():
    """Find all Python files in agent directories."""
    agent_files = []
    
    # Main PC agent directories
    main_pc_dirs = [
        'main_pc_code/agents',
        'main_pc_code/FORMAINPC',
        'main_pc_code/src/core',
        'main_pc_code/src/memory',
        'main_pc_code/src/audio',
        'main_pc_code/src/vision'
    ]
    
    # PC2 agent directories
    pc2_dirs = [
        'pc2_code/agents',
        'pc2_code/agents/ForPC2',
        'pc2_code/agents/core_agents'
    ]
    
    # Exclude directories
    exclude_dirs = [
        'backups', 
        '_archive', 
        '_trash_2025-06-13',
        'needtoverify',
        'agent_backups'
    ]
    
    # Find all Python files
    for directory in main_pc_dirs + pc2_dirs:
        if os.path.exists(directory):
            for root, dirs, files in os.walk(directory):
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for file in files:
                    if file.endswith('.py'):
                        agent_files.append(os.path.join(root, file))
    
    return agent_files

def check_syntax(file_path):
    """Check Python syntax for a file."""
    try:
        py_compile.compile(file_path, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)
    except SyntaxError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def main():
    agent_files = find_agent_files()
    logging.info(f"Found {len(agent_files)} agent files to check")
    
    errors = []
    
    for file_path in agent_files:
        success, error = check_syntax(file_path)
        if success:
            logging.info(f"✓ {file_path}")
        else:
            logging.error(f"✗ {file_path}: {error}")
            errors.append((file_path, error))
    
    if errors:
        logging.error(f"Found {len(errors)} files with syntax errors:")
        for file_path, error in errors:
            logging.error(f"  - {file_path}: {error}")
        return 1
    else:
        logging.info("All agent files passed syntax check!")
        return 0

if __name__ == "__main__":
    sys.exit(main()) 